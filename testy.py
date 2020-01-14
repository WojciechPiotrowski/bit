import tkinter as tk
import aaa
import os
import master_file
import time
import re
import pandas as pd
import db_madras as madras
import SOprog

con = madras.engine.connect()

week = 202001

# st18d = pd.read_excel(r'C:\wojto\___NO\inputy\Storedir_DVH_2018_old.xls', 'omsaar2018')
# st18s = pd.read_excel(r'C:\wojto\___NO\inputy\Storedir_SERVICE_2018_old.xls', 'omsaar2018')
st19d = pd.read_excel(r'C:\wojto\___NO\inputy\Storedir_DVH_2018.xls', 'omsaar2018')
st19s = pd.read_excel(r'C:\wojto\___NO\inputy\Storedir_SERVICE_2018.xls', 'omsaar2018')

st = pd.concat([st19d, st19s], ignore_index=True)
st = st[(st['START'] == week) | (st['END'] == int(SOprog.calc_week(SOprog.calc_period(week)-1)))]

sam = pd.read_excel(r'C:\wojto\___NO\inputy\Sample_copy.xlsx', 'Sample')[['EDBNR', 'MTNR']]

st = pd.merge(st, sam, how='left')

print(st)
quit()

def cells_for_shops(country, period):
    # query na wartosci charakterystyk dla listy sklepow
    SQL_statement2 = '''
                     Select ACV_SHO_ID, CHR_SHORT_DESCRIPTION, CHV_VALUE
                     from Madras_Data.TRSH_ASSIGNED_SHOP_CHAR_VALUE
                     join Madras_Data.TRSH_SHOP_CHAR_VALUE
                     on ACV_CHV_ID = CHV_ID
                     join Madras_Data.TRSH_SHOP_CHARACTERISTIC
                     on ACV_CHV_CHR_ID = CHR_ID
                     where ACV_WEEK_EFFECTIVE_FROM <= {period}
                     and (ACV_WEEK_EFFECTIVE_TO >= {period} or ACV_WEEK_EFFECTIVE_TO is NULL)
                     and chr_cou_code = '{country}'
                     '''

    # getting chars from sql
    outpt = con.execute(SQL_statement2.format(country=country, period=period))
    char_table = pd.DataFrame(outpt.fetchall(), columns=['ACV_SHO_ID', 'ACV_CHV_CHR_ID', 'ACV_CHV_ID'])

    # query na rule cel/PS
    SQL_statement3 = '''
                     Select RSQ_KEY2_ID, RSQ_SQL 
                     from Madras_Data.TMRE_RESENTY_RULE_DISPLAY 
                     where RSQ_KEY2_ID in (Select CEL_ID from Madras_Data.TMXP_CELL 
                                           where cel_sam_id in ({samples})
                                           and CEL_WEEK_EFFECTIVE_TO is NULL)
                     '''
    # query variables
    SQL_statement3 = SQL_statement3.format(samples='164, 1000189, 1000197')
    # calling query
    outpt = con.execute(SQL_statement3)
    # saving sql query result to DataFrame
    active_cells = pd.DataFrame(outpt.fetchall(), columns=['cel_id', 'cel_rule'])

    # patern = re.compile(r"(\w+) (=|IN|NOT IN) \(?(('(.+?)'(?:, )?)+\)?)")
    patern = re.compile(r"((?:\w+ )?\w+) (?:(=) '(.+?)'|(IN|NOT IN) (\((?:'(.+?)'(?:, )?)+\)))")

    # iteracja po sklepach (do inputow powinno po wszystkich aktywnych ze storedira)
    # i nastepnie iteracja po rulach cel i ewaluacja czy rule jest spelniony
    sho_dict = {}
    start_time = time.time()
    for j, shop in char_table.iterrows():
        sho_dict[shop['ACV_SHO_ID']] = []
        sho_table = char_table[char_table['ACV_SHO_ID'] == shop['ACV_SHO_ID']]
        for i, row in active_cells.iterrows():
            rule = str(row['cel_rule'])
            for match in patern.finditer(row['cel_rule']):
                if sho_table[sho_table['ACV_CHV_CHR_ID'] == match[1]].empty:
                    rule = rule.replace(match[0], 'False')
                else:
                    if match[2] == '=':
                        rule = rule.replace(match[0], str(sho_table[sho_table['ACV_CHV_CHR_ID'] == match[1]]['ACV_CHV_ID'].values[0] == match[3]))
                    else:
                        rule = rule.replace(match[0], str(eval("str(char_table[char_table['ACV_CHV_CHR_ID'] == match[1]]['ACV_CHV_ID'].values[0]) in match[5]")))
            rule = rule.replace('AND', 'and')
            rule = rule.replace('OR', 'or')
            # print(rule)
            try:
                evall = eval(rule)
            except:
                evall = False
            if evall:
                sho_dict[shop['ACV_SHO_ID']].append(row['cel_id'])
        end_time = time.time()
        print(j, '   ', int(end_time - start_time))
        sho_dict[shop['ACV_SHO_ID']] = [sho_dict[shop['ACV_SHO_ID']]]
    # na koncu powstaje slownik {sho_id_1: [[cel, cel, PS]], sho_id_2: [[cel, cel]], sho_id_3: [[]]} <- tam jest podwojna lista zeby dalo sie to bez problemow przeformatowac do DataFrame'u
    # pd.DataFrame(causal_cells_for_shops).T (transpozycja jest istotna), sklepy koncza wtedy jako indexy! - przyklad w linii 173
    # w sumie pewnie moznaby przerobic return zeby zrwacal juz transponowany dataframe, ale dziala wiec po co psuc :P
    return sho_dict

cele = pd.DataFrame(cells_for_shops('NO', SOprog.calc_period(week)), index=['CEL_IDs']).T

print(cele)

cele.to_csv(r'C:\wojto\___NO\inputy\cele.csv', ';')

# outtable = pd.DataFrame(columns=['MTNR', 'week_from', 'week_to'])
#
# print(outtable)

# root = tk.Tk()

# aaa.main()

# root.mainloop()