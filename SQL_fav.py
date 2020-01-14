def SMR(period, country, L4L=0):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()
        print(L4L)
        if not L4L:
            print('not')
            query = """
            select SMC_ID, SMC_DESCRIPTION, SMR_ERROR_FLG 
            from madras_data.tmms_smr_resolution_status, MADRAS_DATA.TMMS_SHOP_MAPPED_CHAR 
            where smr_tpr_id = {period} 
            AND SMC_ID =SMR_SMC_ID 
            AND SMC_COU_CODE ='{country}' 
            """.format(period=period, country=country)
        elif L4L:
            print('yes')
            query = """
            select SMC_ID, SMC_DESCRIPTION, SMR_ERROR_FLG 
            from madras_data.tmms_smr_resolution_status, MADRAS_DATA.TMMS_SHOP_MAPPED_CHAR 
            where SMR_SMC_ID in (4786,4787,4788,4789,4790,4791,8651,10671,10670,13674,16960,16961,16962,16963,7739,19295) 
            AND SMC_ID =SMR_SMC_ID 
            AND SMC_COU_CODE ='DK'
            """

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # calling query
        outpt = con.execute(query)
        # saving sql query result to DataFrame
        table = pd.DataFrame(outpt.fetchall(), columns=['SMC_ID', 'SMC_DESCRIPTION', 'SMR_ERROR_FLG'])

        table = table[table['SMR_ERROR_FLG'] != '0']

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if table.empty:
            print('\nSMR error flag check OK\n')
            SOprog.showmessage('SMR error flag check', 'SMR error flag check OK')
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

        else:
            print(table)
            SOprog.showoutput2('SMR error flag check', ('SMR error flag =/= 0', table))
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

def MSR(period, country, L4L=0):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()

        channel = country + 'SCAN'

        if not L4L:
            query = """
            select MMS_MAS_ID, MMS_STATUS, MMS_SAM_ID
            from Madras_Data.TMMS_MS_MAPPING_STATUS 
            where MMS_CCH_ID = ('{channel}') 
            and mms_tpr_id = {period}
            """.format(channel=channel, period=period)
        elif L4L:
            query = """
            Select MMS_MAS_ID, MMS_STATUS, MMS_SAM_ID 
            from Madras_Data.TMMS_MS_MAPPING_STATUS 
            where MMS_MAS_ID in (1262200,1262201,1262236,1262237,1262238,1262195,1334785,1361580,1361585,1361583,1361582, 
            1361584,1361581,1390901,1409473,1409487,1409488,1409489,1409490,1409493,1409491,1409492,1409481,1409482,1409585,
            1409483,1409484,1409485,1409486,1409474,1409475,1409480,1409477,1409479,1409478,1409476,1423436,1423444,1423445,
            1423447,1423448,1423449,1423446,1423450,1423451,1423452,1423776,1423455,1423454,1423453,1423777,1423437,1423438,
            1423443,1423442,1423441,1423439,1423440,1423422,1423429,1423430,1423434,1423433,1423431,1423435,1423432,1423428,
            1423770,1423771,1423772,1423773,1423774,1423775,1423423,1423424,1423768,1423769,1423427,1423425,1423426,1423387,
            1423395,1423396,1423401,1423400,1423398,1423399,1423397,1423402,1423403,1423759,1423405,1423760,1423406,1423404,
            1423388,1423389,1423393,1423392,1423394,1423391,1423390,1423407,1423408,1423409,1423413,1423411,1423410,1423761,
            1423412,1423419,1423420,1423767,1423421,1423764,1423765,1423766,1423414,1423415,1423416,1423763,1423417,1423762,
            1423418,1423456,1423465,1423466,1423469,1423468,1423467,1423784,1423470,1423457,1423458,1423781,1423779,1423778,
            1423780,1423459,1423460,1423461,1423463,1423783,1423462,1423782,1423464,1423371,1423381,1423382,1423383,1423386,
            1423384,1423758,1423385,1423378,1423379,1423757,1423380,1423756,1423754,1423755,1423372,1423373,1423377,1423374,
            1423375,1423753,1423376,1423358,1423359,1423360,1423364,1423363,1423361,1423747,1423362,1423365,1423748,1423795,
            1423750,1423793,1423749,1423794,1423366,1423367,1423368,1423752,1423369,1423751,1423370,1423471,1423479,1423480,
            1423484,1423481,1423482,1423792,1423483,1423472,1423785,1423790,1423787,1423788,1423786,1423789,1423473,1423474,
            1423478,1423475,1423476,1423791,1423477,1427322,1427324,1427325,1427323) 
            and MMS_CCH_ID='DKSCAN'
            """

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # calling query
        outpt = con.execute(query)
        # saving sql query result to DataFrame
        table = pd.DataFrame(outpt.fetchall(), columns=['MMS_MAS_ID', 'MMS_STATUS', 'MMS_SAM_ID'])

        table = table[(table['MMS_STATUS'] != 'ENOSHOP') & (table['MMS_STATUS'] != 'RESOLVED')]

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if table.empty:
            print('\nMMS_STATUS check OK\n')
            SOprog.showmessage('MMS_STATUS check OK', 'MMS_STATUSes are only "RESOLVED" and "ENOSHOP"')
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

        else:
            print(table)
            SOprog.showoutput2('MMS_STATUS check', ('Wrong MMS_STATUS', table))
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

def CELL_CONTENT(period, country, cel_id):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()

        channel = country + 'SCAN'

        new_query = """
        Select sho_external_code From Madras_Data.TRSH_SHOP where sho_id in
            (Select cco_sho_id from Madras_Data.TMXP_CELL_CONTENT 
            where CCO_TPR_ID = {period} 
            and CCO_CEL_ID = {cel_id} 
            and CCO_CCH_ID = '{channel}' 
            and cco_sho_id not in (
                Select cco_sho_id from Madras_Data.TMXP_CELL_CONTENT 
                where CCO_TPR_ID = {period}-1 
                and CCO_CEL_ID = {cel_id} 
                and CCO_CCH_ID = '{channel}'
                )
            )
        """.format(period=period, channel=channel, cel_id=cel_id)

        removed_query = """
        Select sho_external_code From Madras_Data.TRSH_SHOP where sho_id in
            (Select cco_sho_id from Madras_Data.TMXP_CELL_CONTENT 
            where CCO_TPR_ID = {period}-1
            and CCO_CEL_ID = {cel_id}  
            and CCO_CCH_ID = '{channel}' 
            and cco_sho_id not in (
                Select cco_sho_id from Madras_Data.TMXP_CELL_CONTENT 
                where CCO_TPR_ID = {period}
                and CCO_CEL_ID = {cel_id}  
                and CCO_CCH_ID = '{channel}'
                )
            )
        """.format(period=period, channel=channel, cel_id=cel_id)

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # calling query
        new_outpt = con.execute(new_query)
        removed_outpt = con.execute(removed_query)
        # saving sql query result to DataFrame
        new = pd.DataFrame(new_outpt.fetchall(), columns=['sho_external_code'])
        removed = pd.DataFrame(removed_outpt.fetchall(), columns=['sho_external_code'])

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if new.empty and removed.empty:
            SOprog.showmessage('No changes in this cell', 'The content of this cell is the same as in previous week')
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period
        else:
            SOprog.showoutput2('Changes in cell ' + cel_id, ('New shops in cell ' + cel_id, new), ('Shops removed from cell' + cel_id, removed))
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

def SHO_ID(period, country, shops):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()

        shops = shops.replace('\n', ',')
        shops = shops.replace(',,', ',')
        shops = shops.replace("'", '')
        shops_list = shops.split(',')
        # shops_list = list(filter(len, shops_list))
        for shop in shops_list:
            shop = "'" + shop + "'"

        query = """
        Select Sho_id, Sho_external_code 
        from Madras_r.TRSH_SHOP 
        where sho_external_code in ({shops})
        """.format(shops=str(shops_list)[1:-1])

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # calling query
        outpt = con.execute(query)
        # saving sql query result to DataFrame
        table = pd.DataFrame(outpt.fetchall(), columns=['sho_id', 'sho_external_code'])

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if table.empty:
            print('\nNo shops found\n')
            SOprog.showmessage('No shops found', 'No shops with given external codes has been found found')
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

        else:
            print(table)
            SOprog.showoutput2("sho_id's", ('', table))
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

def SHO_EX(period, country, shops):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()

        query = """
        Select Sho_id, Sho_external_code 
        from Madras_r.TRSH_SHOP 
        where sho_id in ({shops})
        """.format(shops=shops)

        # initializing connection with sql MADRAS tables
        con = madras.engine.connect()
        # calling query
        outpt = con.execute(query)
        # saving sql query result to DataFrame
        table = pd.DataFrame(outpt.fetchall(), columns=['sho_id', 'sho_external_code'])

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if table.empty:
            print('\nNo shops found\n')
            SOprog.showmessage('No shops found', "No shops with given id's has been found found")
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

        else:
            print(table)
            SOprog.showoutput2("sho_external_codes", ('', table))
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

def MAS_HII(period, country, mhi_id):
    import db_madras as madras
    import pandas as pd
    import SOprog
    import time

    try:
        start_time = time.time()

        mhi_id = mhi_id.replace('\n', ',')
        mhi_id = mhi_id.replace(',,', ',')
        mhi_id = mhi_id.replace("'", '')
        mhi_id_list = mhi_id.split(',')
        # shops_list = list(filter(len, shops_list))
        # for mhi in mhi_id_list:
        #     mhi = "'" + mhi + "'"

        for mhi in mhi_id_list:
            query1 = """
            Select mas_id, mas_description, hiu_hii_id, hiu_level 
            From Madras_Data.TMMS_MS_HIE_USAGE join Madras_Data.TMMS_MARKET_SEGMENT on mas_id = hiu_mas_id
            where HIU_MAS_ID in (Select HIU_MAS_ID From Madras_Data.TMMS_MS_HIE_USAGE 
                                 where HIU_HII_ID in (Select HII_ID From Madras_Data.TMMS_MS_HIERARCHY_INSTANCE 
                                                      where HII_MHI_ID = {MHI_ID})) 
                                                      and hiu_hii_id not in (Select HII_ID From Madras_Data.TMMS_MS_HIERARCHY_INSTANCE 
                                                                             where HII_MHI_ID = {MHI_ID})
    
            """.format(MHI_ID=mhi)

            query2 = """
            select mas_id, mas_description
            from Madras_Data.TMMS_MS_HIE_USAGE join Madras_Data.TMMS_MARKET_SEGMENT on mas_id = hiu_mas_id
            where HIU_HII_ID in (Select HII_ID From Madras_Data.TMMS_MS_HIERARCHY_INSTANCE where HII_MHI_ID = :MHI_ID)
            and mas_id not in (Select distinct(mas_id)
                               From Madras_Data.TMMS_MS_HIE_USAGE join Madras_Data.TMMS_MARKET_SEGMENT on mas_id = hiu_mas_id
                               where HIU_MAS_ID in (Select HIU_MAS_ID From Madras_Data.TMMS_MS_HIE_USAGE 
                                                    where HIU_HII_ID in (Select HII_ID From Madras_Data.TMMS_MS_HIERARCHY_INSTANCE 
                                                                         where HII_MHI_ID = :MHI_ID)) and 
                                                                         hiu_hii_id not in (Select HII_ID From Madras_Data.TMMS_MS_HIERARCHY_INSTANCE 
                                                                                            where HII_MHI_ID = :MHI_ID))
            """.format(MHI_ID=mhi)
            # initializing connection with sql MADRAS tables
            con = madras.engine.connect()
            # calling query
            outpt = con.execute(query)
            # saving sql query result to DataFrame
            table = pd.DataFrame(outpt.fetchall(), columns=['mas_id', 'mas_description', 'hiu_hii_id', 'hiu_level'])

        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

        if table.empty:
            print('\nNo shops found\n')
            SOprog.showmessage('No shops found', "No shops with given id's has been found found")
            return 'Finished', str(int(end_time - start_time)) + ' sec', country, period

        else:
            print(table)
            SOprog.showoutput2("sho_external_codes", ('', table))
            return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country, period

# def gregSMR(period, country):
#     import db_madras as madras
#     import pandas as pd
#     import SOprog
#     import time
#
#     if country != 'DK':
#         return 'ERROR', 'wrong country', country, period
#
#     try:
#         start_time = time.time()
#
#         # check SMR-a dla L4L
#         query = """
#         select * from madras_data.tmms_smr_resolution_status, MADRAS_DATA.TMMS_SHOP_MAPPED_CHAR
#         where SMR_SMC_ID in (4786,4787,4788,4789,4790,4791,8651,10671,10670,13674,16960,16961,16962,16963,7739,19295)
#         AND SMC_ID =SMR_SMC_ID
#         AND SMC_COU_CODE ='DK'
#         """
#
#         # initializing connection with sql MADRAS tables
#         con = madras.engine.connect()
#         # calling query
#         outpt = con.execute(query)
#         # saving sql query result to DataFrame
#         table = pd.DataFrame(outpt.fetchall(), columns=['sho_id', 'sho_external_code'])
#
#         end_time = time.time()
#         print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')
#
#         if table.empty:
#             print('\nNo shops found\n')
#             SOprog.showmessage('No shops found', "No shops with given id's has been found found")
#             return 'Finished', str(int(end_time - start_time)) + ' sec', country, period
#
#         else:
#             print(table)
#             SOprog.showoutput2("sho_external_codes", ('', table))
#             return 'Finished with output', str(int(end_time - start_time)) + ' sec', country, period
#
#
#     except Exception:
#         import traceback
#         traceback.print_exc()
#         return 'ERROR', traceback.format_exc(), country, period
#
# def gregMSR(period, country):
#     import db_madras as madras
#     import pandas as pd
#     import SOprog
#     import time
#
#     if country != 'DK':
#         return 'ERROR', 'wrong country', country, period
#
#     try:
#         start_time = time.time()
#
#         # check po MRS-rze dla L4L
#         query = """
#         Select * from Madras_Data.TMMS_MS_MAPPING_STATUS
#         where MMS_MAS_ID in (1262200,1262201,1262236,1262237,1262238,1262195,1334785,1361580,1361585,1361583,1361582,
#         1361584,1361581,1390901,1409473,1409487,1409488,1409489,1409490,1409493,1409491,1409492,1409481,1409482,1409585,
#         1409483,1409484,1409485,1409486,1409474,1409475,1409480,1409477,1409479,1409478,1409476,1423436,1423444,1423445,
#         1423447,1423448,1423449,1423446,1423450,1423451,1423452,1423776,1423455,1423454,1423453,1423777,1423437,1423438,
#         1423443,1423442,1423441,1423439,1423440,1423422,1423429,1423430,1423434,1423433,1423431,1423435,1423432,1423428,
#         1423770,1423771,1423772,1423773,1423774,1423775,1423423,1423424,1423768,1423769,1423427,1423425,1423426,1423387,
#         1423395,1423396,1423401,1423400,1423398,1423399,1423397,1423402,1423403,1423759,1423405,1423760,1423406,1423404,
#         1423388,1423389,1423393,1423392,1423394,1423391,1423390,1423407,1423408,1423409,1423413,1423411,1423410,1423761,
#         1423412,1423419,1423420,1423767,1423421,1423764,1423765,1423766,1423414,1423415,1423416,1423763,1423417,1423762,
#         1423418,1423456,1423465,1423466,1423469,1423468,1423467,1423784,1423470,1423457,1423458,1423781,1423779,1423778,
#         1423780,1423459,1423460,1423461,1423463,1423783,1423462,1423782,1423464,1423371,1423381,1423382,1423383,1423386,
#         1423384,1423758,1423385,1423378,1423379,1423757,1423380,1423756,1423754,1423755,1423372,1423373,1423377,1423374,
#         1423375,1423753,1423376,1423358,1423359,1423360,1423364,1423363,1423361,1423747,1423362,1423365,1423748,1423795,
#         1423750,1423793,1423749,1423794,1423366,1423367,1423368,1423752,1423369,1423751,1423370,1423471,1423479,1423480,
#         1423484,1423481,1423482,1423792,1423483,1423472,1423785,1423790,1423787,1423788,1423786,1423789,1423473,1423474,
#         1423478,1423475,1423476,1423791,1423477,1427322,1427324,1427325,1427323)
#         and MMS_CCH_ID='DKSCAN'
#         """
#
#         end_time = time.time()
#         print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')
#
#     except Exception:
#         import traceback
#         traceback.print_exc()
#         return 'ERROR', traceback.format_exc(), country, period

# SMR(1075, 'NO')