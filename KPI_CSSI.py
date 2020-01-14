def main(period, country, storedir):
    import SOprog
    import db_madras as madras
    import pandas as pd
    import numpy as np
    import time

    try:
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 1000)

        start_time = time.time()

        channel = country + 'SCAN'
        week = int(SOprog.calc_week(period))
        lidl = pd.read_excel(storedir)
        lidl_cells = {'SE': (2204986, 2204987, 2204988, 2204990),
                      'DK': (2197059),}

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # query
        SQL_statement = '''
        Select ROUND(sum(cin_x_factor), 2)
        from Madras_Data.TMXP_CELL_INDUSTRY
        where CIN_CCH_ID = '{channel}'
        and CIN_CEL_ID in {cells}
        and CIN_TPR_ID = {period}
        '''.format(channel=channel, period=period, cells=lidl_cells[country])

        # calling query
        outpt = con.execute(SQL_statement)

        # Number of open stores in the universe
        if country == 'SE':
            lidl = lidl[lidl['kednamn'] == 'LIDL']
            lidl = lidl[lidl['start'] <= week]
            lidl = lidl[lidl['end']=='.']
        elif country == 'DK':
            lidl = lidl[lidl['KATEGORI'] == 150]
            lidl = lidl[lidl['start'] <= week]
            lidl = lidl[lidl['end'].isnull()]
        rows = len(lidl.index)
        print('\n\n\n\n\nNumber of open stores in the universe:', rows)

        # Number of total opening hours in the open stores in the universe
        days = ['Mon_From', 'Mon_To', 'Tue_From', 'Tue_To', 'Wed_From', 'Wed_To', 'Thu_From', 'Thu_To',
                'Fri_From', 'Fri_To', 'Sat_From', 'Sat_To', 'Sun_From', 'Sun_To']

        if country == 'SE':
            # Mon_From	Mon_To	Tue_From	Tue_To	Wed_From	Wed_To	Thu_From	Thu_To	Fri_From	Fri_To	Sat_From	Sat_To	Sun_From	Sun_To
            missing = lidl[['start','end','dlfkod','shop','kednamn','butnamn','adress',
                            'Mon_From','Mon_To','Tue_From','Tue_To','Wed_From','Wed_To','Thu_From','Thu_To','Fri_From','Fri_To',
                            'Sat_From','Sat_To','Sun_From','Sun_To']]
        elif country == 'DK':
            # mon_from	tue_from	wed_from	thu_from	fri_from	sat_from	sun_from	mon_to	tue_to	wed_to	thu_to	fri_to	sat_to	sun_to
            days = str(days).lower()[2:-2].split("', '")
            missing = lidl[['start','end','storeid','shop','banner','name','address',
                            'mon_from','mon_to','tue_from','tue_to','wed_from','wed_to','thu_from','thu_to','fri_from','fri_to',
                            'sat_from','sat_to','sun_from','sun_to']]

        missing = missing[missing[(missing[days]=='.')].any(axis=1)]

        lidl[days] = lidl[days].replace('.', np.nan)
        mean = round(lidl[days].mean(skipna=True).apply(int))
        for day in days:
            lidl[day] = lidl[day].replace(np.nan, mean[day]).apply(int)
            # lidl['{day}'.format(day=day)] = lidl['{day}'.format(day=day)].replace(np.nan, mean['{day}'.format(day=day)]).apply(int)

        if missing.empty == False:
            blankIndex = [''] * len(missing)
            missing.index = blankIndex
            print('\nShops with missing hours:\n', missing)
            SOprog.showoutput2('Shops with missing hours', ('', missing))

        plus = 0
        minus = 0
        for day in days:
            if '_to' in day or '_To' in day:
                plus += lidl[day].sum()
            if '_from' in day or '_From' in day:
                minus += lidl[day].sum()
        print('\nNumber of total opening hours in the open stores in the universe:', plus-minus)

        # Number of open stores matching the current slot design
        count = 0
        if country == 'SE':
            for i, row in lidl.iterrows():
                if row['Mon_From'] == 8 and row['Mon_To'] == 21 \
                        and row['Tue_From'] == 9 and row['Tue_To'] == 20 \
                        and row['Wed_From'] == 8 and row['Wed_To'] == 21 \
                        and row['Thu_From'] == 9 and row['Thu_To'] == 20 \
                        and row['Fri_From'] == 8 and row['Fri_To'] == 21 \
                        and row['Sat_From'] == 9 and row['Sat_To'] == 18 \
                        and row['Sun_From'] == 9 and row['Sun_To'] == 18:
                    count += 1
        elif country == 'DK':
            for i, row in lidl.iterrows():
                if row['mon_from'] == 8 and row['mon_to'] == 22 \
                        and row['tue_from'] == 8 and row['tue_to'] == 22 \
                        and row['wed_from'] == 8 and row['wed_to'] == 22 \
                        and row['thu_from'] == 8 and row['thu_to'] == 21 \
                        and row['fri_from'] == 8 and row['fri_to'] == 21 \
                        and row['sat_from'] == 8 and row['sat_to'] == 21 \
                        and row['sun_from'] == 8 and row['sun_to'] == 21:
                    count += 1

        print('\nNumber of open stores matching the current slot design:', count)

        # Sum of XF for the last period in the 4 weeks
        sql_table = pd.DataFrame(outpt.fetchall())
        print('\nSum of XF for the last period in the 4 weeks:', sql_table[0][0])

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        SOprog.showmessage('KPI for CSSI',
                           '\nNumber of open stores in the universe: '+str(rows)+'\n'+
                           '\nNumber of total opening hours in the open stores in the universe: '+str(plus-minus)+'\n'
                           '\nNumber of open stores matching the current slot design: '+str(count)+'\n'
                           '\nSum of XF for the last period in the 4 weeks: '+str(sql_table[0][0]))

        if missing.empty == False:
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period
        else:
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

# main(1069, 'SE', r'C:\wojto\_SE\lidl\storedir18N.xlsx')
# main(1071, 'DK', r'G:\Storedir\storedir19c.xlsx')

