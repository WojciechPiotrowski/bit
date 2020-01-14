import pandas as pd
import time
import math
import SOprog

def main(country, period, pathSample, pathSampleOld):
    try:
        # Start time of program
        start_time = time.time()

        # Setting periods
        periodToWeek = SOprog.calc_week(period)
        previousPeriod = str(int(periodToWeek) - 1)

        # Loading Sample files
        print("Loading Sample files for period: " + str(periodToWeek))
        # sampleNew = pd.read_excel(pathSample + r'\Sample.xlsx', sheet_name='Sample')
        sampleNew = pd.read_excel(pathSampleOld + r'\Sample{}.xlsx'.format(periodToWeek), sheet_name='Sample')
        sampleOld = pd.read_excel(pathSampleOld + r'\Sample{}.xlsx'.format(previousPeriod), sheet_name='Sample')

        # Limiting dataframes to columns used for future computations
        sampleNew = sampleNew[['EDBNR', 'MTNR', 'RTLNR', 'ActiveInSample', 'ActiveInCausalSample', 'Postnr', "Index", 'NO_RETAILER', 'NO_SALGSKJEDE', 'NO_KONSEPTKJEDE', 'NC_SURFACE', 'ACV']]
        sampleOld = sampleOld[['EDBNR', 'MTNR', 'RTLNR', 'ActiveInSample', 'ActiveInCausalSample', 'Postnr', "Index", 'NO_RETAILER', 'NO_SALGSKJEDE', 'NO_KONSEPTKJEDE', 'NC_SURFACE', 'ACV']]

        # Limiting new sample dataframe only to shop active in sample
        sampleNew = sampleNew[sampleNew['ActiveInSample'] == "YES"]

        # Reseting index
        sampleNew = sampleNew.reset_index(drop=True)
        sampleOld = sampleOld.reset_index(drop=True)

        # Creating characteristics for both samples
        sampleNew = creating_char(sampleNew, periodToWeek)
        sampleOld = creating_char(sampleOld, previousPeriod)

        print("Saving samples to Excel")
        sampleNew.to_excel(r'C:\Users\kose9001\Desktop\Norway\Test\{}sampleNew.xlsx'.format(periodToWeek))
        sampleOld.to_excel(r'C:\Users\kose9001\Desktop\Norway\Test\{}sampleOld.xlsx'.format(periodToWeek))

        # print("Loading Sample files")
        # sampleNew = pd.read_excel(r'C:\Users\kose9001\Desktop\Norway\Test\{}sampleNew.xlsx'.format(periodToWeek), index_col=0)
        # sampleOld = pd.read_excel(r'C:\Users\kose9001\Desktop\Norway\Test\{}sampleOld.xlsx'.format(periodToWeek), index_col=0)

        # Creating ShopCharAssignment file
        charDataframe, message = shopCharAssignment(sampleNew, sampleOld, periodToWeek, previousPeriod)

        # Testing
        if charDataframe.empty != True:
            testing(charDataframe, periodToWeek)
        else:
            pass

        # End time of program + duration
        end_time = time.time()
        print('\n\n\n', int(end_time - start_time), 'sec\n\n\n')

    except Exception:
        import traceback
        traceback.print_exc()
        return 'ERROR', traceback.format_exc(), country

def creating_char(sample, period):
        # Creating characteristics
        # Basic characteriscics
        print("Creating basic characteristics")
        sample["Period"] = period
        sample["CHANNEL"] = "SCAN"
        sample["COUNTRY"] = "NO"

        # Characteristics created based on postnumber
        print("Characteristics created based on postnumber")
        charList = {"BAT1": bat, "BORD": bord, "MAA2": maa2, "MAA4": maa4, "NO_STANDARD_AREA": standardArea, "NO_MONDELEZ REGION": mondelez,
                    "OR17": or17, "OR18": or18, "ORK2": ork2, "ORK3": ork3, "REB1": reb1,
                    "RIN3": rin3, "RIN4": rin4, "RIN5": rin5, "RIN6": rin6, "SWM3": swm3, "SWM4": swm4, "SWM5": swm5, "TIN3": tin3}

        for key, value in charList.items():
            sample[key] = sample["Postnr"].map(lambda postnumber: value(postnumber) if (postnumber != '.') else "")

        # Other characteristics
        print("Creating other characteristics")
        sample["OMSKL"] = sample["ACV"].map(lambda acv: (acv / 10) if (acv != '.') else "")
        sample["NO_OMSETNINGSGRUPPE_KOB"] = sample.apply(lambda sample: omsetning_kob(sample["OMSKL"]) if ((sample['Index'] == "Service") & (sample["OMSKL"] != ""))else "", axis=1)
        sample["NO_OMSETNINGSGRUPPE_DVH"] = sample.apply(lambda sample: omsetning_dvh(sample["OMSKL"]) if ((sample['Index'] == "Dagligvare")& (sample["OMSKL"] != "")) else "", axis=1)

        sample["NO_SHOPTYPE"] = sample.apply(lambda sample: 1 if sample['Index'] == "Dagligvare" else "", axis=1)
        sample["NO_SHOPTYPE"] = sample.apply(lambda sample: 2 if ((sample['Index'] == "Dagligvare") & (sample['NO_RETAILER'] in [911, 913, 915])) else sample["NO_SHOPTYPE"], axis=1)
        sample["NO_SHOPTYPE"] = sample.apply(lambda sample: 2 if ((sample['Index'] == "Dagligvare") & (sample['NO_KONSEPTKJEDE'] == 850)) else sample["NO_SHOPTYPE"], axis=1)
        sample["NO_SHOPTYPE"] = sample.apply(lambda sample: 4 if (sample['Index'] == "Service") else sample["NO_SHOPTYPE"], axis=1)

        sample["NO_CAUSAL"] = sample["ActiveInCausalSample"].map(lambda activeCausal: causal(activeCausal))
        sample["NO_AREA"] = sample["NO_STANDARD_AREA"].map(lambda stanArea: area(stanArea))
        sample["NO_SHOPSIZE"] = sample["NC_SURFACE"].map(lambda surface: shopsize(surface) if (surface != '.') else "")

        # Regional characteristics
        print("Creating regional characteristics")
        columnList = ["NO_KOMMUNEKOD", "hdi", "NO_MODUL1", "district", "NO_kreg", "New_Fylke", "New_kommune"]
        for column in columnList:
            print("Creating column " + column)
            sample[column] = sample["Postnr"].map(lambda postnumber: regionalChar(postnumber, charType=column) if (postnumber != '.') else "")

        sample["NO_MODUL_CELL"] = sample["NO_MODUL1"].map(lambda modul: nomodul(modul))
        sample["Fylke"] = sample["NO_KOMMUNEKOD"].map(lambda komkod: fylke(komkod))

        return sample

def shopCharAssignment(sampleNew, sampleOld, periodToWeek, previousPeriod):
    print("Creating ShopCharAssignment file")
    # Merging samples
    sampleConcat = pd.concat([sampleNew, sampleOld], axis=0, ignore_index=True, sort=False)
    sampleConcat.reset_index(drop=True)

    # Renaming columns
    sampleConcat.rename(columns={'NC_SURFACE': 'NO_SURFACE', 'Fylke': 'NO_FYLKE', 'New_Fylke': "NO_NEWFYLKE",
                                 'New_kommune': 'NO_NEWKOMMUNEKOD', 'Postnr': 'NO_POSTNR'}, inplace=True)

    # Creating column subset for droping dupicates and further calculations
    columnSubset = list(sampleConcat.columns)
    excludedColumns = ['Period', 'ACV', 'OMSKL', 'EDBNR', 'RTLNR', "ActiveInSample", "Index"]
    for column in excludedColumns:
        columnSubset.remove(column)

    # Dropping duplicate rows with the same values
    sampleConcat = sampleConcat.drop_duplicates(subset=columnSubset, keep=False, inplace=False)
    sampleConcat.sort_values(['MTNR'], inplace=True)
    sampleConcat.reset_index(drop=True)
    sampleConcat.fillna(value='', inplace=True)

    # Getting rows with the same MTNR number
    duplicates = sampleConcat['MTNR'].duplicated(keep=False)

    # Shops with changed characteristics
    sampleDuplicates = sampleConcat[duplicates]

    # New shops
    sampleUnique = sampleConcat[~duplicates]
    sampleUnique = sampleUnique[sampleUnique['Period'] == periodToWeek]

    # importing NewShops file for future computation
    try:
        NewShops = pd.read_csv(r'R:\BAU\NewWeek\Madras\{}\NewShops.csv'.format(periodToWeek), delimiter=";", header=None, encoding='utf-8', usecols=[0])
        NewShops.columns = ["MTNR"]
        NewShops["MTNR"] = NewShops.apply(lambda NewShops: int(NewShops["MTNR"]) - 1800000000, axis=1)
        newShops = NewShops["MTNR"].tolist()
    except FileNotFoundError:
        print("There are no new shops in this period")

    # Getting changed characteristics
    dataChanged = []
    for i, row in sampleDuplicates.iterrows():
        for j, row2 in sampleDuplicates.iterrows():
            # In case new shop is already in sample but changed status "ActivInSample" from "NO" to "YES"
            if row["ActiveInSample"] != row2["ActiveInSample"] and row2["ActiveInSample"] == "YES" and ((row2['MTNR'] in newShops) == True):
                for c in columnSubset:
                    if type(row2[c]) != str:
                        data = {"MTNR": row2['MTNR'], "Char": c, "Char_Value": int(row2[c])}
                    else:
                        data = {"MTNR": row2['MTNR'], "Char": c, "Char_Value": row2[c]}
                    dataChanged.append(data)
            elif row['MTNR'] == row2['MTNR'] and row2["Period"] == periodToWeek:
                for c in columnSubset:
                    if row[c] != row2[c] and c != "ActiveInSample":
                        if type(row2[c]) != str:
                            data = {"MTNR": row2['MTNR'], "Char": c, "Char_Value": int(row2[c])}
                        else:
                            data = {"MTNR": row2['MTNR'], "Char": c, "Char_Value": row2[c]}
                        dataChanged.append(data)

    # Exception handling ActiveInCausalSample issue
    # for i, row in sampleDuplicates.iterrows():
    #     for j, row2 in sampleDuplicates.iterrows():
    #         if row['MTNR'] == row2['MTNR'] and row["ActiveInSample"] == "NO" and row2["ActiveInSample"] == "YES" and row2["ActiveInCausalSample"] == "NO" and row['MTNR'] not in dataChanged:
    #             data = {"MTNR": row2['MTNR'], "Char": "NO_CAUSAL", "Char_Value": row2["NO_CAUSAL"]}


    charChanged = pd.DataFrame(dataChanged)

    # Getting new characteristics
    dataNew = []
    for i, row in sampleUnique.iterrows():
        for c in columnSubset:
            if (type(row[c]) != str):
                data = {"MTNR": row['MTNR'], "Char": c, "Char_Value": int(row[c])}
            else:
                data = {"MTNR": row['MTNR'], "Char": c, "Char_Value": row[c]}
            dataNew.append(data)

    charNew = pd.DataFrame(dataNew)

    # Creating characteristic dataframes
    charDataframe = pd.concat([charChanged, charNew], axis=0, ignore_index=True, sort=False)

    if charDataframe.empty == True:
        message = "No changes or new characteristics for period: " + str(periodToWeek)
        print(message)
        return charDataframe, message
    else:
        message = "There are changes or new characteristics for period: " + str(periodToWeek)
        print(message)

        # Reshaping characteristic dataframe
        charDataframe = charDataframe.drop_duplicates(keep="first", inplace=False)
        charDataframe["MTNR"] = charDataframe.apply(lambda charDataframe: 1800000000 + charDataframe["MTNR"], axis=1)
        charDataframe.sort_values(by=["MTNR", "Char"], inplace=True)
        charDataframe = charDataframe[["MTNR", "Char", "Char_Value"]]

        # Dropping unnecessary characteristics
        if int(periodToWeek) >= 201944:
            unnecessaryChar = ["MTNR", "NO_STANDARD_AREA", "NO_kreg", "district", "hdi", "ActiveInCausalSample"]
            for char in unnecessaryChar:
                charDataframe = charDataframe.drop(charDataframe[charDataframe['Char'] == char].index)
        else:
            unnecessaryChar = ["MTNR", "NO_STANDARD_AREA", "NO_kreg", "district", "hdi", "ActiveInCausalSample", 'NO_NEWFYLKE', "NO_NEWKOMMUNEKOD"]
            for char in unnecessaryChar:
                charDataframe = charDataframe.drop(charDataframe[charDataframe['Char'] == char].index)

        # Dropping chars with empty values
        charDataframe = charDataframe.drop(charDataframe[charDataframe['Char_Value'] == ""].index)
        charDataframe = charDataframe.drop(charDataframe[charDataframe['Char_Value'] == "."].index)

        # Saving to excel
        print("Saving to Excel")
        charDataframe.to_csv(r'C:\Users\kose9001\Desktop\Norway\Test\{}ShopCharAssignment.csv'.format(periodToWeek), header=False, index=False, sep=";")

        return charDataframe, message

def testing(charDataframe, period):

    print('Testing dataframe with source file - period: ' + str(period))
    shopCharAssignment = pd.read_csv(r'R:\BAU\NewWeek\Madras\{}\ShopCharAssignment.csv'.format(period), delimiter=";", header=None)

    charDataframe["Type"] = "Python dataframe"
    shopCharAssignment.columns = ["MTNR", "Char", "Char_Value"]
    shopCharAssignment['Type'] = "Production dataframe"

    shopCharAssignment.reset_index(drop=True, inplace=True)
    charDataframe.reset_index(drop=True, inplace=True)

    shopCharAssignment["Char_Value"] = shopCharAssignment.apply(lambda shopCharAssignment: int(shopCharAssignment["Char_Value"]) if ((shopCharAssignment["Char"] != "CHANNEL") & (shopCharAssignment["Char"] != "COUNTRY")) else shopCharAssignment["Char_Value"], axis=1)

    # Merging samples
    charConcat = pd.concat([charDataframe, shopCharAssignment], axis=0, ignore_index=False, sort=False)
    charConcat.reset_index(drop=True)

    # Dropping duplicate rows
    charConcat = charConcat.drop_duplicates(subset=["MTNR", "Char", "Char_Value"], keep=False, inplace=False)

    # Getting rows with the same MTNR number
    duplicates = charConcat.duplicated(subset=["MTNR", "Char", "Char_Value"], keep=False)

    # Shops with changed characteristics
    charDuplicates = charConcat[duplicates]

    # New shops
    charUnique = charConcat[~duplicates]

    if charConcat.empty == True:
        charDataframe.to_csv(r'C:\Users\kose9001\Desktop\Norway\Test\{}ShopCharAssignment-correct.csv'.format(period), header=False, index=False)
        print("Correct file for period: " + str(period))
    else:
        charConcat.to_csv(r'C:\Users\kose9001\Desktop\Norway\Test\{}ShopCharAssignment-incorrect.csv'.format(period), header=False, index=False)
        print("Incorrect file for period: " + str(period))

# Functions assigning characteristics based on conditions
def bat(postnumber):
    batCond1 = (((postnumber >= 550) & (postnumber <= 575)) | ((postnumber >= 580) & (postnumber <= 581)) |
                ((postnumber >= 585) & (postnumber <= 592)) | ((postnumber >= 598) & (postnumber <= 621)) |
                ((postnumber >= 1479) & (postnumber <= 1479)) | ((postnumber >= 2000) & (postnumber <= 2027)) |
                ((postnumber >= 2040) & (postnumber <= 2058)) | ((postnumber >= 2063) & (postnumber <= 2069)) |
                ((postnumber >= 2635) & (postnumber <= 2635)) | ((postnumber >= 2639) & (postnumber <= 2695)))

    batCond2 = (((postnumber >= 470) & (postnumber <= 470)) | ((postnumber >= 481) & (postnumber <= 481)) |
                ((postnumber >= 484) & (postnumber <= 486)) | ((postnumber >= 576) & (postnumber <= 579)) |
                ((postnumber >= 593) & (postnumber <= 597)) | ((postnumber >= 650) & (postnumber <= 663)) |
                ((postnumber >= 950) & (postnumber <= 1112)) | ((postnumber >= 1470) & (postnumber <= 1476)) |
                ((postnumber >= 1900) & (postnumber <= 1970)) | ((postnumber >= 2100) & (postnumber <= 2266)) )

    batCond3 = (((postnumber >= 8300) & (postnumber <= 8398)) | ((postnumber >= 8601) & (postnumber <= 9134)) |
                ((postnumber >= 9138) & (postnumber <= 9140)) | ((postnumber >= 9276) & (postnumber <= 9991)))

    batCond4 = (((postnumber >= 8000) & (postnumber <= 8298)) | ((postnumber >= 8400) & (postnumber <= 8591)) |
                ((postnumber >= 9135) & (postnumber <= 9136)) | ((postnumber >= 9141) & (postnumber <= 9275)))

    batCond5 = (((postnumber >= 1440) & (postnumber <= 1448)) | ((postnumber >= 1501) & (postnumber <= 1892)))

    batCond6 = (((postnumber >= 3001) & (postnumber <= 3058)) | ((postnumber >= 3300) & (postnumber <= 3519)) |
                ((postnumber >= 3533) & (postnumber <= 3632)))

    batCond7 = (((postnumber >= 267) & (postnumber <= 349)) | ((postnumber >= 373) & (postnumber <= 440)) |
                ((postnumber >= 751) & (postnumber <= 850)) | ((postnumber >= 1300) & (postnumber <= 1397)) |
                ((postnumber >= 3530) & (postnumber <= 3531)))

    batCond8 = (((postnumber >= 188) & (postnumber <= 244)) | ((postnumber >= 664) & (postnumber <= 750)) |
                ((postnumber >= 1150) & (postnumber <= 1295)) | ((postnumber >= 1400) & (postnumber <= 1432)) |
                ((postnumber >= 1450) & (postnumber <= 1458)))

    batCond9 = (((postnumber >= 2270) & (postnumber <= 2634)) | ((postnumber >= 2636) & (postnumber <= 2637)) |
                ((postnumber >= 2801) & (postnumber <= 2858)))

    batCond10 = (((postnumber >= 10) & (postnumber <= 152)) | ((postnumber >= 154) & (postnumber <= 155)) |
                 ((postnumber >= 181) & (postnumber <= 181)) | ((postnumber >= 184) & (postnumber <= 187)) |
                 ((postnumber >= 582) & (postnumber <= 584)) | ((postnumber >= 1480) & (postnumber <= 1488)) |
                 ((postnumber >= 2030) & (postnumber <= 2034)) | ((postnumber >= 2060) & (postnumber <= 2061)) |
                 ((postnumber >= 2070) & (postnumber <= 2093)) | ((postnumber >= 2711) & (postnumber <= 2770)) |
                 ((postnumber >= 2860) & (postnumber <= 2985)) | ((postnumber >= 3520) & (postnumber <= 3529)))

    batCond11 = (((postnumber >= 153) & (postnumber <= 153)) | ((postnumber >= 157) & (postnumber <= 180)) |
                 ((postnumber >= 182) & (postnumber <= 183)) | ((postnumber >= 250) & (postnumber <= 266)) |
                 ((postnumber >= 350) & (postnumber <= 372)) | ((postnumber >= 445) & (postnumber <= 469)) |
                 ((postnumber >= 473) & (postnumber <= 480)) | ((postnumber >= 482) & (postnumber <= 483)) |
                 ((postnumber >= 487) & (postnumber <= 540)) | ((postnumber >= 851) & (postnumber <= 915)))

    batCond12 = (((postnumber >= 3060) & (postnumber <= 3296)) | ((postnumber >= 3646) & (postnumber <= 3658)))

    batCond13 = (((postnumber >= 5003) & (postnumber <= 5007)) | ((postnumber >= 5009) & (postnumber <= 5012)) |
                 ((postnumber >= 5014) & (postnumber <= 5050)) | ((postnumber >= 5054) & (postnumber <= 5055)) |
                 ((postnumber >= 5057) & (postnumber <= 5058)) | ((postnumber >= 5063) & (postnumber <= 5071)) |
                 ((postnumber >= 5075) & (postnumber <= 5137)) | ((postnumber >= 5163) & (postnumber <= 5163)) |
                 ((postnumber >= 5200) & (postnumber <= 5222)) | ((postnumber >= 5229) & (postnumber <= 5232)) |
                 ((postnumber >= 5260) & (postnumber <= 5299)) | ((postnumber >= 5600) & (postnumber <= 5620)) |
                 ((postnumber >= 5650) & (postnumber <= 5658)) | ((postnumber >= 5700) & (postnumber <= 5745)) |
                 ((postnumber >= 5747) & (postnumber <= 5748)) | ((postnumber >= 5802) & (postnumber <= 5994)) |
                 ((postnumber >= 6851) & (postnumber <= 6899)))

    batCond14 = (((postnumber >= 6001) & (postnumber <= 6699)) | ((postnumber >= 6779) & (postnumber <= 6799)) |
                 ((postnumber >= 6823) & (postnumber <= 6848)))

    batCond15 = (((postnumber >= 7025) & (postnumber <= 7025)) | ((postnumber >= 7029) & (postnumber <= 7029)) |
                 ((postnumber >= 7036) & (postnumber <= 7036)) | ((postnumber >= 7038) & (postnumber <= 7038)) |
                 ((postnumber >= 7041) & (postnumber <= 7041)) | ((postnumber >= 7043) & (postnumber <= 7043)) |
                 ((postnumber >= 7048) & (postnumber <= 7048)) | ((postnumber >= 7051) & (postnumber <= 7056)) |
                 ((postnumber >= 7072) & (postnumber <= 7074)) | ((postnumber >= 7079) & (postnumber <= 7079)) |
                 ((postnumber >= 7081) & (postnumber <= 7082)) | ((postnumber >= 7091) & (postnumber <= 7091)) |
                 ((postnumber >= 7239) & (postnumber <= 7239)) | ((postnumber >= 7500) & (postnumber <= 7570)) |
                 ((postnumber >= 7590) & (postnumber <= 7994)))

    batCond16 = (((postnumber >= 3660) & (postnumber <= 3999)) | ((postnumber >= 4801) & (postnumber <= 4836)) |
                 ((postnumber >= 4841) & (postnumber <= 4846)) | ((postnumber >= 4851) & (postnumber <= 4855)) |
                 ((postnumber >= 4863) & (postnumber <= 4869)) | ((postnumber >= 4900) & (postnumber <= 4994)) |
                 ((postnumber >= 7240) & (postnumber <= 7240)))

    batCond17 = (((postnumber >= 4400) & (postnumber <= 4401)) | ((postnumber >= 4480) & (postnumber <= 4795)) |
                 ((postnumber >= 4838) & (postnumber <= 4839)) | ((postnumber >= 4847) & (postnumber <= 4849)) |
                 ((postnumber >= 4856) & (postnumber <= 4859)) | ((postnumber >= 4870) & (postnumber <= 4898)) |
                 ((postnumber >= 7241) & (postnumber <= 7241)))

    batCond18 = (((postnumber >= 5008) & (postnumber <= 5008)) | ((postnumber >= 5013) & (postnumber <= 5013)) |
                 ((postnumber >= 5052) & (postnumber <= 5053)) | ((postnumber >= 5056) & (postnumber <= 5056)) |
                 ((postnumber >= 5059) & (postnumber <= 5059)) | ((postnumber >= 5072) & (postnumber <= 5073)) |
                 ((postnumber >= 5141) & (postnumber <= 5162)) | ((postnumber >= 5164) & (postnumber <= 5184)) |
                 ((postnumber >= 5223) & (postnumber <= 5228)) | ((postnumber >= 5235) & (postnumber <= 5259)) |
                 ((postnumber >= 5300) & (postnumber <= 5419)) | ((postnumber >= 6700) & (postnumber <= 6778)) |
                 ((postnumber >= 6800) & (postnumber <= 6821)) | ((postnumber >= 6900) & (postnumber <= 6996)) |
                 ((postnumber >= 7242) & (postnumber <= 7242)))

    batCond19 = (((postnumber >= 4001) & (postnumber <= 4006)) | ((postnumber >= 4011) & (postnumber <= 4011)) |
                 ((postnumber >= 4013) & (postnumber <= 4014)) | ((postnumber >= 4035) & (postnumber <= 4035)) |
                 ((postnumber >= 4042) & (postnumber <= 4042)) | ((postnumber >= 4050) & (postnumber <= 4088)) |
                 ((postnumber >= 4092) & (postnumber <= 4187)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                 ((postnumber >= 4420) & (postnumber <= 4473)) | ((postnumber >= 7243) & (postnumber <= 7243)))

    batCond20 = (((postnumber >= 4007) & (postnumber <= 4010)) | ((postnumber >= 4012) & (postnumber <= 4012)) |
                 ((postnumber >= 4015) & (postnumber <= 4034)) | ((postnumber >= 4041) & (postnumber <= 4041)) |
                 ((postnumber >= 4043) & (postnumber <= 4049)) | ((postnumber >= 4089) & (postnumber <= 4091)) |
                 ((postnumber >= 4198) & (postnumber <= 4299)) | ((postnumber >= 5420) & (postnumber <= 5598)) |
                 ((postnumber >= 5626) & (postnumber <= 5649)) | ((postnumber >= 5680) & (postnumber <= 5696)) |
                 ((postnumber >= 5746) & (postnumber <= 5746)) | ((postnumber >= 5750) & (postnumber <= 5787)) |
                 ((postnumber >= 7246) & (postnumber <= 7246)))

    batCond21 = (((postnumber >= 7002) & (postnumber <= 7024)) | ((postnumber >= 7026) & (postnumber <= 7028)) |
                 ((postnumber >= 7030) & (postnumber <= 7034)) | ((postnumber >= 7037) & (postnumber <= 7037)) |
                 ((postnumber >= 7039) & (postnumber <= 7040)) | ((postnumber >= 7042) & (postnumber <= 7042)) |
                 ((postnumber >= 7044) & (postnumber <= 7047)) | ((postnumber >= 7049) & (postnumber <= 7050)) |
                 ((postnumber >= 7057) & (postnumber <= 7070)) | ((postnumber >= 7075) & (postnumber <= 7078)) |
                 ((postnumber >= 7080) & (postnumber <= 7080)) | ((postnumber >= 7083) & (postnumber <= 7089)) |
                 ((postnumber >= 7092) & (postnumber <= 7238)) | ((postnumber >= 7247) & (postnumber <= 7496)) |
                 ((postnumber >= 7580) & (postnumber <= 7584)))

    conditionList = [batCond1, batCond2, batCond3, batCond4, batCond5, batCond6, batCond7, batCond8, batCond9, batCond10,
                     batCond11, batCond12, batCond13, batCond14, batCond15, batCond16, batCond17, batCond18, batCond19, batCond20,
                     batCond21]

    def conditioncheck(conditions):
        bat = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                bat = index + 1
        return bat

    bat = conditioncheck(conditionList)

    return bat

def bord(postnumber):
    bordCond1 = (((postnumber >= 10) & (postnumber <= 2093)) | ((postnumber >= 2135) & (postnumber <= 2219)) |
            ((postnumber >= 2224) & (postnumber <= 2226)) | ((postnumber >= 2241) & (postnumber <= 2283)) |
            ((postnumber >= 2392) & (postnumber <= 2438)) | ((postnumber >= 2449) & (postnumber <= 2460)) |
            ((postnumber >= 2713) & (postnumber <= 2713)) | ((postnumber >= 2715) & (postnumber <= 2743)) |
            ((postnumber >= 2986) & (postnumber <= 3331)) | ((postnumber >= 3372) & (postnumber <= 3428)) |
            ((postnumber >= 3698) & (postnumber <= 3749)) | ((postnumber >= 3792) & (postnumber <= 3792)) |
            ((postnumber >= 3896) & (postnumber <= 3999)))

    bordCond2 = (((postnumber >= 6997) & (postnumber <= 7099)) | ((postnumber >= 7207) & (postnumber <= 7238)) |
             ((postnumber >= 7288) & (postnumber <= 7310)) | ((postnumber >= 7320) & (postnumber <= 7330)) |
             ((postnumber >= 7346) & (postnumber <= 7358)) | ((postnumber >= 7375) & (postnumber <= 7387)) |
             ((postnumber >= 7400) & (postnumber <= 7634)))

    bordCond3 = (((postnumber >= 2094) & (postnumber <= 2134)) | ((postnumber >= 2220) & (postnumber <= 2223)) |
             ((postnumber >= 2227) & (postnumber <= 2240)) | ((postnumber >= 2284) & (postnumber <= 2391)) |
             ((postnumber >= 2439) & (postnumber <= 2448)) | ((postnumber >= 2461) & (postnumber <= 2712)) |
             ((postnumber >= 2714) & (postnumber <= 2714)) | ((postnumber >= 2744) & (postnumber <= 2985)) |
             ((postnumber >= 3332) & (postnumber <= 3371)) | ((postnumber >= 3429) & (postnumber <= 3697)) |
             ((postnumber >= 3750) & (postnumber <= 3791)) | ((postnumber >= 3793) & (postnumber <= 3895)) |
             ((postnumber >= 4000) & (postnumber <= 6996)) | ((postnumber >= 7100) & (postnumber <= 7206)) |
             ((postnumber >= 7239) & (postnumber <= 7287)) | ((postnumber >= 7311) & (postnumber <= 7319)) |
             ((postnumber >= 7331) & (postnumber <= 7345)) | ((postnumber >= 7359) & (postnumber <= 7374)) |
             ((postnumber >= 7388) & (postnumber <= 7399)) | ((postnumber >= 7635) & (postnumber <= 9991)))

    bord = ''
    if bordCond1 is True:
        bord = 1
    elif bordCond2 is True:
        bord = 2
    elif bordCond3 is True:
        bord = 3

    return bord

def maa2(postnumber):
    maaCond1 = (((postnumber >= 10) & (postnumber <= 137)) | ((postnumber >= 150) & (postnumber <= 169)) |
                ((postnumber >= 171) & (postnumber <= 486)) | ((postnumber >= 493) & (postnumber <= 493)) |
                ((postnumber >= 496) & (postnumber <= 551)) | ((postnumber >= 553) & (postnumber <= 562)) |
                ((postnumber >= 564) & (postnumber <= 573)) | ((postnumber >= 577) & (postnumber <= 581)) |
                ((postnumber >= 583) & (postnumber <= 588)) | ((postnumber >= 601) & (postnumber <= 654)) |
                ((postnumber >= 656) & (postnumber <= 663)) | ((postnumber >= 701) & (postnumber <= 857)) |
                ((postnumber >= 860) & (postnumber <= 861)) | ((postnumber >= 873) & (postnumber <= 880)))

    maaCond2 = (((postnumber >= 139) & (postnumber <= 139)) | ((postnumber >= 676) & (postnumber <= 679)) |
                ((postnumber >= 682) & (postnumber <= 688)) | ((postnumber >= 690) & (postnumber <= 691)) |
                ((postnumber >= 693) & (postnumber <= 694)) | ((postnumber >= 1150) & (postnumber <= 1153)) |
                ((postnumber >= 1155) & (postnumber <= 1295)) | ((postnumber >= 1400) & (postnumber <= 1459)) |
                ((postnumber >= 1911) & (postnumber <= 1914)))

    maaCond3 = (((postnumber >= 170) & (postnumber <= 170)) | ((postnumber >= 487) & (postnumber <= 492)) |
                ((postnumber >= 494) & (postnumber <= 495)) | ((postnumber >= 552) & (postnumber <= 552)) |
                ((postnumber >= 563) & (postnumber <= 563)) | ((postnumber >= 574) & (postnumber <= 576)) |
                ((postnumber >= 582) & (postnumber <= 582)) | ((postnumber >= 589) & (postnumber <= 598)) |
                ((postnumber >= 655) & (postnumber <= 655)) | ((postnumber >= 664) & (postnumber <= 675)) |
                ((postnumber >= 680) & (postnumber <= 681)) | ((postnumber >= 689) & (postnumber <= 689)) |
                ((postnumber >= 692) & (postnumber <= 692)) | ((postnumber >= 858) & (postnumber <= 858)) |
                ((postnumber >= 862) & (postnumber <= 872)) | ((postnumber >= 881) & (postnumber <= 1112)) |
                ((postnumber >= 1154) & (postnumber <= 1154)) | ((postnumber >= 1470) & (postnumber <= 1488)) |
                ((postnumber >= 2005) & (postnumber <= 2006)) | ((postnumber >= 2008) & (postnumber <= 2015)) |
                ((postnumber >= 2022) & (postnumber <= 2027)))

    maaCond4 = (((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3400) & (postnumber <= 3491)))

    maaCond5 = (((postnumber >= 1501) & (postnumber <= 1892)) | ((postnumber >= 1930) & (postnumber <= 1970)))

    maaCond6 = (((postnumber >= 1900) & (postnumber <= 1910)) | ((postnumber >= 1920) & (postnumber <= 1929)) |
                ((postnumber >= 2000) & (postnumber <= 2004)) | ((postnumber >= 2007) & (postnumber <= 2007)) |
                ((postnumber >= 2016) & (postnumber <= 2021)) | ((postnumber >= 2030) & (postnumber <= 2170)))

    maaCond7 = ((postnumber >= 2200) & (postnumber <= 2487))

    maaCond8 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 6640) & (postnumber <= 6660)) |
                ((postnumber >= 6674) & (postnumber <= 6699)) | ((postnumber >= 7002) & (postnumber <= 7499)) |
                ((postnumber >= 7540) & (postnumber <= 7570)))

    maaCond9 = (((postnumber >= 2600) & (postnumber <= 2695)) | ((postnumber >= 2801) & (postnumber <= 2868)))

    maaCond10 = (((postnumber >= 2711) & (postnumber <= 2770)) | ((postnumber >= 2870) & (postnumber <= 3058)) |
                 ((postnumber >= 3300) & (postnumber <= 3387)) | ((postnumber >= 3501) & (postnumber <= 3599)) |
                 ((postnumber >= 3627) & (postnumber <= 3632)))

    maaCond11 = (((postnumber >= 3060) & (postnumber <= 3296)) | ((postnumber >= 3646) & (postnumber <= 3648)))

    maaCond12 = (((postnumber >= 3601) & (postnumber <= 3626)) | ((postnumber >= 3650) & (postnumber <= 3999)) |
                 ((postnumber >= 4747) & (postnumber <= 4755)) | ((postnumber >= 4971) & (postnumber <= 5003)))

    maaCond13 = (((postnumber >= 4001) & (postnumber <= 4198)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                 ((postnumber >= 4420) & (postnumber <= 4443)) | ((postnumber >= 4462) & (postnumber <= 4462)))

    maaCond14 = (((postnumber >= 4200) & (postnumber <= 4299)) | ((postnumber >= 5142) & (postnumber <= 5151)) |
                 ((postnumber >= 5200) & (postnumber <= 5248)) | ((postnumber >= 5252) & (postnumber <= 5258)) |
                 ((postnumber >= 5335) & (postnumber <= 5335)) | ((postnumber >= 5384) & (postnumber <= 5454)) |
                 ((postnumber >= 5460) & (postnumber <= 5463)) | ((postnumber >= 5472) & (postnumber <= 5472)) |
                 ((postnumber >= 5501) & (postnumber <= 5595)) | ((postnumber >= 5635) & (postnumber <= 5636)) |
                 ((postnumber >= 5640) & (postnumber <= 5641)) | ((postnumber >= 5650) & (postnumber <= 5650)) |
                 ((postnumber >= 5728) & (postnumber <= 5729)) | ((postnumber >= 6721) & (postnumber <= 6737)) |
                 ((postnumber >= 6800) & (postnumber <= 6996)))

    maaCond15 = (((postnumber >= 4400) & (postnumber <= 4401)) | ((postnumber >= 4460) & (postnumber <= 4460)) |
                 ((postnumber >= 4463) & (postnumber <= 4745)) | ((postnumber >= 4760) & (postnumber <= 4951)))

    maaCond16 = (((postnumber >= 5004) & (postnumber <= 5141)) | ((postnumber >= 5152) & (postnumber <= 5184)) |
                 ((postnumber >= 5251) & (postnumber <= 5251)) | ((postnumber >= 5259) & (postnumber <= 5334)) |
                 ((postnumber >= 5336) & (postnumber <= 5382)) | ((postnumber >= 5455) & (postnumber <= 5459)) |
                 ((postnumber >= 5464) & (postnumber <= 5470)) | ((postnumber >= 5473) & (postnumber <= 5499)) |
                 ((postnumber >= 5596) & (postnumber <= 5632)) | ((postnumber >= 5637) & (postnumber <= 5637)) |
                 ((postnumber >= 5642) & (postnumber <= 5649)) | ((postnumber >= 5652) & (postnumber <= 5727)) |
                 ((postnumber >= 5730) & (postnumber <= 5994)))

    maaCond17 = (((postnumber >= 6001) & (postnumber <= 6639)) | ((postnumber >= 6670) & (postnumber <= 6670)) |
                 ((postnumber >= 6700) & (postnumber <= 6719)) | ((postnumber >= 6740) & (postnumber <= 6799)))

    maaCond18 = (((postnumber >= 7500) & (postnumber <= 7533)) | ((postnumber >= 7580) & (postnumber <= 7994)) |
                 ((postnumber >= 8900) & (postnumber <= 8985)))

    maaCond19 = (((postnumber >= 8000) & (postnumber <= 8493)) | ((postnumber >= 8534) & (postnumber <= 8539)) |
                 ((postnumber >= 8600) & (postnumber <= 8892)))

    maaCond20 = (((postnumber >= 8501) & (postnumber <= 8533)) | ((postnumber >= 8540) & (postnumber <= 8591)) |
                 ((postnumber >= 9000) & (postnumber <= 9991)))


    conditionList = [maaCond1, maaCond2, maaCond3, maaCond4, maaCond5, maaCond6, maaCond7, maaCond8, maaCond9,
                     maaCond10, maaCond11, maaCond12, maaCond13, maaCond14, maaCond15, maaCond16, maaCond17, maaCond18,
                     maaCond19, maaCond20]

    def conditioncheck(conditions):
        maa2 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                maa2 = index + 1
        return maa2

    maa2 = conditioncheck(conditionList)

    return maa2

def maa4(postnumber):
    maaCond1 = (((postnumber >= 4001) & (postnumber <= 4198)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                ((postnumber >= 4432) & (postnumber <= 4443)) | ((postnumber >= 4462) & (postnumber <= 4463)))

    maaCond2 = (((postnumber >= 4200) & (postnumber <= 4299)) | ((postnumber >= 5142) & (postnumber <= 5147)) |
                ((postnumber >= 5200) & (postnumber <= 5222)) | ((postnumber >= 5224) & (postnumber <= 5248)) |
                ((postnumber >= 5252) & (postnumber <= 5258)) | ((postnumber >= 5335) & (postnumber <= 5335)) |
                ((postnumber >= 5385) & (postnumber <= 5454)) | ((postnumber >= 5459) & (postnumber <= 5463)) |
                ((postnumber >= 5470) & (postnumber <= 5472)) | ((postnumber >= 5498) & (postnumber <= 5596)) |
                ((postnumber >= 5635) & (postnumber <= 5636)) | ((postnumber >= 5640) & (postnumber <= 5641)) |
                ((postnumber >= 5650) & (postnumber <= 5650)) | ((postnumber >= 5680) & (postnumber <= 5683)) |
                ((postnumber >= 5690) & (postnumber <= 5690)) | ((postnumber >= 5728) & (postnumber <= 5729)) |
                ((postnumber >= 5913) & (postnumber <= 5913)) | ((postnumber >= 5960) & (postnumber <= 5960)) |
                ((postnumber >= 5981) & (postnumber <= 5983)) | ((postnumber >= 6721) & (postnumber <= 6737)) |
                ((postnumber >= 6800) & (postnumber <= 6996)))

    maaCond3 = (((postnumber >= 1501) & (postnumber <= 1892)) | ((postnumber >= 1910) & (postnumber <= 1910)) |
                ((postnumber >= 1930) & (postnumber <= 1970)))

    maaCond4 = (((postnumber >= 5003) & (postnumber <= 5141)) | ((postnumber >= 5148) & (postnumber <= 5184)) |
                ((postnumber >= 5223) & (postnumber <= 5223)) | ((postnumber >= 5251) & (postnumber <= 5251)) |
                ((postnumber >= 5259) & (postnumber <= 5334)) | ((postnumber >= 5336) & (postnumber <= 5384)) |
                ((postnumber >= 5455) & (postnumber <= 5458)) | ((postnumber >= 5464) & (postnumber <= 5464)) |
                ((postnumber >= 5473) & (postnumber <= 5497)) | ((postnumber >= 5598) & (postnumber <= 5632)) |
                ((postnumber >= 5637) & (postnumber <= 5637)) | ((postnumber >= 5642) & (postnumber <= 5649)) |
                ((postnumber >= 5652) & (postnumber <= 5658)) | ((postnumber >= 5685) & (postnumber <= 5687)) |
                ((postnumber >= 5693) & (postnumber <= 5727)) | ((postnumber >= 5730) & (postnumber <= 5912)) |
                ((postnumber >= 5914) & (postnumber <= 5957)) | ((postnumber >= 5961) & (postnumber <= 5979)) |
                ((postnumber >= 5984) & (postnumber <= 5994)))

    maaCond5 = (((postnumber >= 1386) & (postnumber <= 1386)) | ((postnumber >= 1389) & (postnumber <= 1391)) |
                ((postnumber >= 1400) & (postnumber <= 1400)) | ((postnumber >= 1405) & (postnumber <= 1408)) |
                ((postnumber >= 1415) & (postnumber <= 1458)) | ((postnumber >= 2936) & (postnumber <= 2937)) |
                ((postnumber >= 3001) & (postnumber <= 3058)) | ((postnumber >= 3300) & (postnumber <= 3414)) |
                ((postnumber >= 3425) & (postnumber <= 3538)))

    maaCond6 = (((postnumber >= 2201) & (postnumber <= 2364)) | ((postnumber >= 2380) & (postnumber <= 2584)) |
                ((postnumber >= 7374) & (postnumber <= 7374)))

    maaCond7 = (((postnumber >= 6001) & (postnumber <= 6639)) | ((postnumber >= 6670) & (postnumber <= 6670)) |
                ((postnumber >= 6700) & (postnumber <= 6719)) | ((postnumber >= 6740) & (postnumber <= 6799)))

    maaCond8 = (((postnumber >= 513) & (postnumber <= 518)) | ((postnumber >= 581) & (postnumber <= 583)) |
                ((postnumber >= 586) & (postnumber <= 598)) | ((postnumber >= 890) & (postnumber <= 1088)) |
                ((postnumber >= 1470) & (postnumber <= 1476)) | ((postnumber >= 1480) & (postnumber <= 1488)) |
                ((postnumber >= 1900) & (postnumber <= 1903)) | ((postnumber >= 1920) & (postnumber <= 1929)) |
                ((postnumber >= 2000) & (postnumber <= 2004)) | ((postnumber >= 2007) & (postnumber <= 2007)) |
                ((postnumber >= 2010) & (postnumber <= 2013)) | ((postnumber >= 2015) & (postnumber <= 2024)) |
                ((postnumber >= 2026) & (postnumber <= 2170)) | ((postnumber >= 2711) & (postnumber <= 2770)))

    maaCond9 = (((postnumber >= 4400) & (postnumber <= 4420)) | ((postnumber >= 4460) & (postnumber <= 4460)) |
                ((postnumber >= 4465) & (postnumber <= 4951)))

    maaCond10 = (((postnumber >= 10) & (postnumber <= 135)) | ((postnumber >= 151) & (postnumber <= 186)) |
                 ((postnumber >= 212) & (postnumber <= 371)) | ((postnumber >= 373) & (postnumber <= 383)) |
                 ((postnumber >= 450) & (postnumber <= 460)) | ((postnumber >= 710) & (postnumber <= 852)) |
                 ((postnumber >= 1300) & (postnumber <= 1385)) | ((postnumber >= 1387) & (postnumber <= 1388)) |
                 ((postnumber >= 1392) & (postnumber <= 1397)) | ((postnumber >= 3420) & (postnumber <= 3421)))

    maaCond11 = (((postnumber >= 3060) & (postnumber <= 3296)) | ((postnumber >= 3646) & (postnumber <= 3648)))

    maaCond12 = (((postnumber >= 139) & (postnumber <= 150)) | ((postnumber >= 187) & (postnumber <= 211)) |
                 ((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 401) & (postnumber <= 445)) |
                 ((postnumber >= 461) & (postnumber <= 511)) | ((postnumber >= 540) & (postnumber <= 580)) |
                 ((postnumber >= 584) & (postnumber <= 585)) | ((postnumber >= 601) & (postnumber <= 705)) |
                 ((postnumber >= 853) & (postnumber <= 884)) | ((postnumber >= 1089) & (postnumber <= 1295)) |
                 ((postnumber >= 1401) & (postnumber <= 1404)) | ((postnumber >= 1409) & (postnumber <= 1414)) |
                 ((postnumber >= 1479) & (postnumber <= 1479)) | ((postnumber >= 1911) & (postnumber <= 1914)) |
                 ((postnumber >= 2005) & (postnumber <= 2006)) | ((postnumber >= 2008) & (postnumber <= 2009)) |
                 ((postnumber >= 2014) & (postnumber <= 2014)) | ((postnumber >= 2025) & (postnumber <= 2025)))

    maaCond13 = (((postnumber >= 8000) & (postnumber <= 8891)) | ((postnumber >= 9441) & (postnumber <= 9444)))

    maaCond14 = (((postnumber >= 3588) & (postnumber <= 3588)) | ((postnumber >= 3601) & (postnumber <= 3632)) |
                 ((postnumber >= 3650) & (postnumber <= 3999)) | ((postnumber >= 4971) & (postnumber <= 4994)))

    maaCond15 = (((postnumber >= 2365) & (postnumber <= 2372)) | ((postnumber >= 2601) & (postnumber <= 2695)) |
                 ((postnumber >= 2801) & (postnumber <= 2933)) | ((postnumber >= 2939) & (postnumber <= 2985)) |
                 ((postnumber >= 3539) & (postnumber <= 3581)) | ((postnumber >= 3593) & (postnumber <= 3595)))

    maaCond16 = (((postnumber >= 7500) & (postnumber <= 7533)) | ((postnumber >= 7580) & (postnumber <= 7994)) |
                 ((postnumber >= 8900) & (postnumber <= 8985)))

    maaCond17 = (((postnumber >= 6640) & (postnumber <= 6660)) | ((postnumber >= 6674) & (postnumber <= 6699)) |
                 ((postnumber >= 7002) & (postnumber <= 7372)) | ((postnumber >= 7380) & (postnumber <= 7496)) |
                 ((postnumber >= 7540) & (postnumber <= 7570)))

    maaCond18 = (((postnumber >= 9000) & (postnumber <= 9440)) | ((postnumber >= 9445) & (postnumber <= 9991)))


    conditionList = [maaCond1, maaCond2, maaCond3, maaCond4, maaCond5, maaCond6, maaCond7, maaCond8, maaCond9,
                     maaCond10, maaCond11, maaCond12, maaCond13, maaCond14, maaCond15, maaCond16, maaCond17, maaCond18]

    def conditioncheck(conditions):
        maa4 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                maa4 = index + 1
        return maa4

    maa4 = conditioncheck(conditionList)

    return maa4

def standardArea(postnumber):
    standartCond1 = (((postnumber >= 5995) & (postnumber <= 6699)) | ((postnumber >= 6997) & (postnumber <= 7977)) |
                     ((postnumber >= 7983) & (postnumber <= 7994)))

    standartCond2 = (((postnumber >= 7978) & (postnumber <= 7982)) | ((postnumber >= 7995) & (postnumber <= 9991)))

    standartCond3 = ((postnumber >= 10) & (postnumber <= 1295))

    standartCond4 = (((postnumber >= 4000) & (postnumber <= 4395)) | ((postnumber >= 4444) & (postnumber <= 4465)) |
                     ((postnumber >= 4995) & (postnumber <= 5994)) | ((postnumber >= 6700) & (postnumber <= 6996)))

    standartCond5 = (((postnumber >= 2986) & (postnumber <= 3519)) | ((postnumber >= 3523) & (postnumber <= 3526)) |
                     ((postnumber >= 3529) & (postnumber <= 3999)) | ((postnumber >= 4396) & (postnumber <= 4443)) |
                     ((postnumber >= 4466) & (postnumber <= 4994)))

    standartCond6 = (((postnumber >= 1296) & (postnumber <= 2985)) | ((postnumber >= 3520) & (postnumber <= 3522)) |
                     ((postnumber >= 3527) & (postnumber <= 3528)))

    conditionList = {"MIDT NORGE": standartCond1, "NORD NORGE": standartCond2, "OSLO": standartCond3,
                     "VEST NORGE": standartCond4, "VESTRE ØSTLAND": standartCond5, "ØSTRE ØSTLAND": standartCond6}

    def conditioncheck(conditions):
        standardArea = ''
        for key, condition in conditions.items():
            if condition is True:
                standardArea = key
        return standardArea

    standardArea = conditioncheck(conditionList)

    return standardArea

def shopsize(surface):
    shopsize = ''
    if (surface > 2499) is True:
        shopsize = 1
    elif ((surface > 999) & (surface <= 2499)) is True:
        shopsize = 2
    elif ((surface > 399) & (surface <= 999)) is True:
        shopsize = 3
    elif ((surface > 99) & (surface <= 399)) is True:
        shopsize = 4
    else:
        shopsize = 5

    return shopsize

def omsetning_kob(omskl):
    Cond1 = ((omskl >= 0) & (omskl < 0.5))

    Cond2 = ((omskl >= 0.5) & (omskl < 1))

    Cond3 = ((omskl >= 1) & (omskl < 2))

    Cond4 = ((omskl >= 2) & (omskl < 4))

    Cond5 = ((omskl >= 4) & (omskl < 6))

    Cond6 = ((omskl >= 6) & (omskl < 9))

    Cond7 = ((omskl >= 9) & (omskl < 12))

    Cond8 = ((omskl >= 12) & (omskl < 15))

    Cond9 = ((omskl >= 15) & (omskl < 20))

    Cond10 = (omskl >= 20)

    conditionList = [Cond1, Cond2, Cond3, Cond4, Cond5, Cond6, Cond7, Cond8, Cond9, Cond10]

    def conditioncheck(conditions):
        omsetning_kob = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                omsetning_kob = index + 1
        return omsetning_kob

    omsetning_kob = conditioncheck(conditionList)

    return omsetning_kob

def omsetning_dvh(omskl):
    Cond1 = ((omskl >= 0) & (omskl < 2))

    Cond2 = ((omskl >= 2) & (omskl < 4))

    Cond3 = ((omskl >= 4) & (omskl < 8))

    Cond4 = ((omskl >= 8) & (omskl < 16))

    Cond5 = ((omskl >= 16) & (omskl < 32))

    Cond6 = ((omskl >= 32) & (omskl < 64))

    Cond7 = ((omskl >= 64) & (omskl < 128))

    Cond8 = ((omskl >= 128) & (omskl < 256))

    Cond9 = ((omskl >= 256) & (omskl < 512))

    Cond10 = ((omskl >= 512) & (omskl < 1024))

    conditionList = [Cond1, Cond2, Cond3, Cond4, Cond5, Cond6, Cond7, Cond8, Cond9, Cond10]

    def conditioncheck(conditions):
        omsetning_dvh = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                omsetning_dvh = index + 1
        return omsetning_dvh


    omsetning_dvh = conditioncheck(conditionList)

    return omsetning_dvh

def causal(activeCausal):
    if activeCausal == "YES":
        causal = 1
    elif activeCausal == "NO" :
        causal = 0

    return causal

def area(stanArea):
    areaDict = {"MIDT NORGE": 5, "NORD NORGE": 6, "OSLO": 1, "VEST NORGE": 4, "VESTRE ØSTLAND": 3, "ØSTRE ØSTLAND": 2}

    def conditioncheck(stanArea, areaDict):
        area = ''
        for key, value in areaDict.items():
            if stanArea == key:
                area = value
        return area

    area = conditioncheck(stanArea, areaDict)

    return area

def regionalChar(postnumber, charType):

    regionalChar = valueDict()

    def conditioncheck(postnumber, regionalChar, charType):
        char = ''
        for key, value in regionalChar.items():
            if postnumber == key:
                char = value[charType]
        return char

    char = conditioncheck(postnumber, regionalChar, charType)

    return char

def mondelez(postnumber):
    range1 = [10,15,16,17,18,19,20,21,22,23,24,25,26,27,28,30,31,32,33,34,35,37,40,41,42,43,45,46,47,48,50,55,56,60,61,
              62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,101,102,103,104,105,106,107,108,109,110,111,112,
              113,114,115,116,117,118,119,120,121,122,123,124,125,127,128,129,130,131,133,134,135,137,139,150,151,152,
              153,154,155,157,158,159,160,161,162,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,
              181,182,183,184,185,186,187, 188,190,191,192,193,196,198,201,202,203,204,207,208,211,212,213,214,215,216,
              230,240,241,242,243,244,245,246,250,251,252,253,254,255,256,257,258,259,260,261,262,263,264,265,266,267,
              268,270,271,272,273,274,275,276,277,278,279,280,281,282,283,284,286,287,301,302,303,304,305,306,307,308,
              309,310,311,312,313,314,315,316,317,318,319,320,323,340,341,342,349,350,351,352,353,354,355,356,357,358,
              359,360,361,362,363,364,365,366,367,368,369,370,371,372,373,374,375,376,377,378,379,380,381,382,383,401,
              402,403,404,405,406,407,408,409,411,421,422,423,424,425,426,440,444,445,450,451,452,454,455,456,457,458,
              459,460,461,462,463,464,465,467,468,469,470,472,473,474,475,476,477,478,479,480,481,482,483,484,485,486,
              487,488,489,490,491,492,493,494,495,496,501,502,503,504,505,506,508,509,510,511,513,514,515,517,518,530,
              531,532,540,550,551,552,553,554,555,556,557,558,559,560,561,562,563,564,565,566,567,568,569,570,571,572,
              573,574,575,576,577,578,579,580,581,582,583,584,585,586,587,588,589,590,591,592,593,594,595,596,597,598,
              601,602,603,604,605,606,607,608,609,611,612,614,615,616,617,619,620,621,640,645,650,651,652,653,654,655,
              656,657,658,659,660,661,662,663,664,665,666,667,668,669,670,671,672,673,674,675,676,677,678,679,680,681,
              682,683,684,685,686,687,688,689,690,691,692,693,694,701,702,705,710,712,750,751,752,753,754,755,756,757,
              758,759,761,764,765,766,767,768,770,771,772,773,774,775,776,777,778,779,781,782,783,784,785,786,787,788,
              789,790,791,801,805,806,807,840,850,851,852,853,854,855,856,857,858,860,861,862,863,864,870,871,872,873,
              874,875,876,877,880,881,882,883,884,890,891,901,902,903,905,907,913,915,950,951,952,953,954,955,956,957,
              958,959,960,962,963,964,966,967,968,969,970,971,972,973,975,976,977,978,979,980,982,983,984,985,986,987,
              988,1001,1006,1007,1008,1009,1011,1051,1052,1053,1054,1055,1056,1061,1062,1063,1064,1065,1067,1068,1069,
              1071,1081,1083,1084,1086,1087,1088,1089,1101,1107,1109,1112,1150,1151,1152,1153,1154,1155,1156,1157,1158,
              1160,1161,1162,1163,1164,1165,1166,1167,1168,1169,1170,1172,1176,1177,1178,1179,1181,1182,1184,1185,1187,
              1188,1189,1201,1202,1203,1204,1206,1207,1212,1214,1215,1250,1251,1252,1253,1254,1255,1256,1257,1258,1259,
              1262,1263,1266,1270,1271,1272,1273,1274,1275,1277,1278,1279,1281,1283,1284,1285,1286,1290,1291,1294,1295,
              1300,1301,1302,1303,1305,1306,1309,1311,1312,1313,1314,1317,1318,1319,1321,1322,1323,1324,1325,1326,1327,
              1330,1332,1333,1334,1336,1337,1338,1339,1340,1341,1344,1346,1348,1349,1350,1351,1352,1353,1354,1355,1356,
              1357,1358,1359,1361,1362,1363,1364,1365,1366,1367,1368,1369,1370,1371,1372,1373,1375,1376,1377,1378,1379,
              1380,1381,1383,1384,1385,1386,1387,1388,1389,1390,1391,1392,1394,1395,1396,1397,1400,1401,1402,1403,1404,
              1405,1406,1407,1408,1409,1410,1411,1412,1413,1414,1415,1416,1417,1420,1430,1431,1432,1440,1441,1443,1444,
              1445,1447,1450,1451,1452,1453,1454,1455,1458,1459,1470,1471,1472,1473,1474,1475,1476,1480,1481,1482,1483,
              1484,1487,1488,1501,1502,1503,1504,1505,1506,1507,1508,1509,1510,1511,1512,1513,1514,1515,1516,1517,1518,
              1519,1520,1521,1522,1523,1524,1525,1526,1527,1528,1529,1530,1531,1532,1533,1534,1535,1536,1537,1538,1539,
              1540,1541,1545,1550,1555,1556,1560,1570,1580,1581,1590,1591,1592,1593,1596,1597,1598,1599,1600,1601,1602,
              1603,1604,1605,1606,1607,1608,1609,1610,1611,1612,1613,1614,1615,1616,1617,1618,1619,1620,1621,1623,1624,
              1625,1626,1627,1628,1629,1630,1631,1632,1633,1634,1635,1636,1637,1638,1639,1640,1641,1642,1650,1651,1653,
              1654,1655,1656,1657,1658,1659,1661,1662,1663,1664,1665,1666,1667,1670,1671,1672,1673,1675,1676,1677,1678,
              1679,1680,1684,1690,1692,1701,1702,1703,1704,1705,1706,1707,1708,1709,1710,1711,1712,1713,1714,1715,1718,
              1719,1720,1721,1722,1723,1724,1725,1726,1727,1728,1729,1730,1733,1734,1735,1738,1739,1740,1742,1743,1745,
              1746,1747,1751,1752,1753,1754,1755,1756,1757,1758,1760,1763,1764,1765,1766,1767,1768,1769,1771,1772,1776,
              1777,1778,1779,1781,1782,1783,1784,1785,1786,1787,1788,1789,1790,1791,1792,1793,1794,1796,1798,1800,1801,
              1802,1803,1804,1805,1806,1807,1808,1809,1811,1812,1813,1814,1815,1816,1820,1823,1825,1827,1830,1831,1832,
              1850,1851,1859,1860,1861,1866,1870,1871,1875,1878,1880,1890,1891,1892,1900,1901,1903,1910,1911,1912,1914,
              1920,1921,1923,1925,1927,1929,1930,1940,1941,1945,1950,1954,1960,1963,1970,2000,2001,2003,2004,2005,2006,
              2007,2008,2009,2010,2011,2013,2014,2015,2016,2019,2020,2021,2022,2024,2025,2026,2027,2030,2031,2032,2033,
              2034,2040,2041,2050,2051,2052,2053,2054,2055,2056,2058,2059,2060,2061,2063,2065,2066,2067,2068,2069,2070,
              2071,2072,2073,2074,2080,2081,2090,2091,2092,2093,2100,2101,2110,2114,2116,2120,2123,2130,2133,2134,2150,
              2151,2160,2162,2164,2165,2166,2170,2200,2201,2202,2203,2204,2205,2206,2208,2209,2210,2211,2212,2213,2214,
              2216,2217,2218,2219,2220,2223,2224,2225,2226,2230,2232,2233,2235,2240,2242,2256,2260,2264,2265,2266,2270,
              2271,2280,2283,2301,2302,2303,2304,2305,2306,2307,2308,2312,2315,2316,2317,2318,2319,2320,2321,2322,2323,
              2324,2325,2326,2327,2328,2329,2330,2332,2334,2335,2337,2338,2340,2344,2345,2350,2353,2355,2360,2364,2365,
              2372,2380,2381,2382,2383,2390,2391,2401,2402,2403,2404,2405,2406,2407,2408,2409,2410,2411,2412,2414,2415,
              2416,2418,2419,2420,2422,2423,2425,2427,2428,2429,2430,2432,2435,2436,2437,2438,2440,2443,2446,2448,2450,
              2451,2460,2476,2477,2478,2480,2482,2485,2486,2487,2500,2501,2510,2512,2540,2542,2544,2550,2552,2555,2560,
              2580,2582,2584,2600,2601,2602,2603,2604,2605,2606,2607,2608,2609,2610,2611,2612,2613,2614,2615,2616,2617,
              2618,2619,2620,2621,2624,2625,2626,2629,2630,2631,2632,2633,2634,2635,2636,2637,2639,2640,2642,2643,2646,
              2647,2648,2649,2651,2652,2653,2656,2657,2658,2659,2660,2661,2662,2663,2665,2666,2667,2668,2669,2670,2671,
              2672,2673,2674,2675,2676,2677,2680,2682,2683,2684,2685,2686,2687,2688,2690,2693,2694,2695,2711,2712,2713,
              2714,2715,2716,2717,2720,2730,2740,2742,2743,2750,2760,2770,2801,2802,2803,2804,2805,2807,2808,2809,2810,
              2811,2813,2815,2816,2817,2818,2819,2821,2822,2825,2827,2830,2831,2832,2836,2837,2838,2839,2840,2843,2846,
              2847,2848,2849,2850,2851,2853,2854,2857,2858,2860,2861,2862,2864,2866,2867,2868,2870,2879,2880,2881,2882,
              2890,2893,2900,2901,2907,2910,2917,2918,2920,2923,2929,2930,2933,2936,2937,2939,2940,2943,2950,2952,2953,
              2959,2960,2966,2967,2973,2975,2977,2985,3001,3002,3003,3004,3005,3006,3007,3008,3009,3011,3012,3013,3014,
              3015,3016,3017,3018,3019,3020,3021,3022,3023,3024,3025,3026,3027,3028,3029,3030,3031,3032,3033,3034,3035,
              3036,3037,3038,3039,3040,3041,3042,3043,3044,3045,3046,3047,3048,3050,3051,3053,3054,3055,3056,3057,3300,
              3301,3303,3320,3321,3322,3330,3331,3340,3341,3350,3351,3355,3358,3359,3360,3361,3370,3371,3387,3400,3401,
              3402,3408,3410,3412,3414,3420,3421,3425,3426,3427,3428,3430,3431,3440,3441,3442,3470,3471,3472,3474,3475,
              3476,3477,3478,3480,3481,3482,3483,3484,3490,3491,3501,3502,3503,3504,3505,3506,3510,3511,3512,3513,3514,
              3515,3516,3517,3518,3519,3520,3521,3522,3524,3525,3526,3528,3529,3530,3531,3533,3534,3535,3536,3537,3538,
              3539,3540,3541,3544,3550,3551,3560,3561,3570,3571,3576,3577,3579,3580,3581,3593,3595,3596,3598,3599,3601,
              3602,3603,3604,3605,3608,3610,3611,3612,3613,3614,3615,3616,3617,3618,3619,3620,3621,3622,3623,3624,3626,
              3627,3628,3629,3630,3631,3632,3646,3647,3648,1442,1448,1479,195,3588,3403,1360,194,2421,2386,2388]
    range2 = [3058,3060,3061,3070,3071,3075,3080,3081,3088,3089,3090,3092,3095,3100,3101,3102,3103,3104,3105,3106,3107,
              3108,3109,3110,3111,3112,3113,3114,3115,3116,3117,3118,3120,3121,3122,3123,3124,3125,3126,3127,3128,3129,
              3131,3132,3133,3135,3140,3142,3143,3144,3145,3147,3148,3150,3151,3152,3153,3154,3157,3158,3159,3160,3161,
              3162,3163,3164,3165,3166,3167,3168,3170,3171,3172,3173,3174,3175,3176,3178,3179,3180,3181,3182,3183,3184,
              3185,3186,3187,3188,3189,3191,3192,3193,3194,3195,3196,3197,3198,3199,3201,3202,3203,3204,3205,3206,3207,
              3208,3209,3210,3211,3212,3213,3214,3215,3216,3217,3218,3219,3220,3221,3222,3223,3224,3225,3226,3227,3228,
              3229,3230,3231,3232,3233,3234,3235,3236,3237,3238,3239,3241,3242,3243,3244,3245,3246,3247,3248,3249,3251,
              3252,3254,3255,3256,3257,3258,3259,3260,3261,3262,3263,3264,3265,3267,3268,3269,3270,3271,3274,3275,3276,
              3277,3280,3282,3285,3290,3291,3292,3294,3295,3296,3650,3652,3656,3658,3660,3661,3665,3666,3671,3672,3673,
              3674,3675,3676,3677,3678,3679,3680,3681,3683,3684,3687,3688,3689,3690,3691,3692,3697,3699,3700,3701,3702,
              3703,3704,3705,3706,3707,3708,3709,3710,3711,3712,3713,3714,3715,3716,3717,3718,3719,3720,3721,3722,3723,
              3724,3725,3726,3727,3728,3729,3730,3731,3732,3733,3734,3735,3736,3737,3738,3739,3740,3741,3742,3743,3744,
              3746,3747,3748,3749,3750,3753,3760,3766,3770,3771,3772,3780,3781,3782,3783,3784,3788,3790,3791,3792,3793,
              3794,3795,3800,3801,3805,3810,3812,3820,3825,3830,3831,3832,3833,3834,3835,3836,3840,3841,3848,3849,3850,
              3853,3854,3855,3860,3864,3870,3880,3882,3883,3884,3885,3886,3887,3888,3890,3891,3893,3895,3900,3901,3902,
              3903,3904,3905,3906,3907,3908,3909,3910,3911,3912,3913,3914,3915,3916,3917,3918,3919,3920,3921,3922,3923,
              3924,3925,3926,3927,3928,3929,3930,3931,3932,3933,3936,3937,3939,3940,3941,3942,3943,3944,3945,3946,3947,
              3948,3949,3950,3960,3962,3965,3966,3970,3991,3993,3995,3999,4001,4002,4003,4004,4005,4006,4007,4008,4009,
              4010,4011,4012,4013,4014,4015,4016,4017,4018,4019,4020,4021,4022,4023,4024,4025,4026,4027,4028,4029,4032,
              4033,4034,4035,4040,4041,4042,4043,4044,4045,4046,4047,4048,4049,4050,4051,4052,4053,4054,4055,4056,4057,
              4064,4065,4066,4067,4068,4069,4070,4076,4080,4085,4086,4088,4089,4090,4091,4092,4093,4094,4095,4096,4097,
              4098,4100,4102,4110,4120,4122,4123,4124,4126,4127,4128,4129,4130,4134,4137,4139,4146,4148,4150,4152,4153,
              4156,4157,4158,4160,4163,4164,4167,4168,4169,4170,4173,4174,4180,4182,4187,4198,4200,4201,4208,4230,4233,
              4234,4235,4237,4238,4239,4240,4244,4250,4260,4262,4264,4265,4270,4272,4274,4275,4276,4280,4291,4294,4295,
              4296,4297,4298,4299,4301,4302,4303,4304,4305,4306,4307,4308,4309,4310,4311,4312,4313,4314,4315,4316,4317,
              4318,4319,4321,4322,4323,4324,4325,4326,4327,4328,4329,4330,4332,4333,4335,4339,4340,4342,4343,4347,4349,
              4350,4352,4353,4354,4355,4356,4358,4360,4362,4363,4364,4365,4367,4368,4369,4370,4372,4373,4375,4376,4379,
              4380,4381,4387,4389,4391,4392,4394,4395,4400,4401,4420,4432,4434,4436,4438,4440,4443,4460,4462,4463,4465,
              4473,4480,4484,4485,4490,4491,4492,4501,4502,4503,4504,4505,4506,4507,4508,4509,4510,4512,4513,4514,4515,
              4516,4517,4519,4520,4521,4525,4528,4529,4532,4534,4536,4540,4544,4550,4551,4557,4558,4560,4563,4575,4576,
              4577,4579,4580,4586,4588,4590,4595,4596,4604,4605,4606,4608,4609,4610,4611,4612,4613,4614,4615,4616,4617,
              4618,4619,4621,4622,4623,4624,4625,4626,4628,4629,4630,4631,4632,4633,4634,4635,4636,4637,4638,4639,4640,
              4641,4645,4646,4647,4656,4657,4658,4659,4661,4662,4663,4664,4665,4666,4668,4669,4671,4673,4674,4675,4676,
              4677,4679,4682,4683,4685,4686,4687,4688,4689,4691,4693,4696,4697,4698,4699,4700,4701,4702,4705,4715,4720,
              4724,4730,4733,4734,4735,4737,4738,4741,4742,4745,4747,4748,4754,4755,4760,4766,4768,4770,4780,4790,4791,
              4792,4795,4800,4801,4802,4803,4808,4809,4810,4812,4815,4816,4817,4818,4820,4821,4823,4824,4825,4827,4828,
              4830,4832,4834,4835,4836,4838,4839,4841,4842,4843,4844,4846,4847,4848,4849,4851,4852,4853,4854,4855,4856,
              4857,4858,4859,4863,4864,4865,4868,4869,4870,4876,4877,4878,4879,4885,4886,4887,4888,4889,4891,4892,4894,
              4895,4896,4898,4900,4901,4909,4910,4912,4915,4916,4920,4934,4950,4951,4971,4972,4973,4974,4980,4985,4990,
              4993,4994,5003,5004,5005,5006,5007,5008,5009,5010,5011,5012,5013,5014,5015,5016,5017,5018,5019,5020,5021,
              5025,5030,5031,5032,5033,5034,5035,5036,5037,5038,5039,5041,5042,5043,5045,5050,5052,5053,5054,5055,5056,
              5057,5058,5059,5063,5067,5068,5071,5072,5073,5075,5081,5089,5093,5094,5096,5097,5098,5099,5101,5104,5105,
              5106,5107,5108,5109,5111,5113,5114,5115,5116,5117,5118,5119,5121,5122,5124,5131,5132,5134,5135,5136,5137,
              5141,5142,5143,5144,5145,5146,5147,5148,5151,5152,5153,5154,5155,5160,5161,5162,5163,5164,5165,5170,5171,
              5172,5173,5174,5176,5177,5178,5179,5183,5184,5200,5201,5202,5203,5204,5207,5208,5209,5210,5211,5212,5215,
              5216,5217,5218,5219,5221,5222,5223,5224,5225,5226,5227,5228,5229,5230,5231,5232,5235,5236,5237,5238,5239,
              5243,5244,5251,5252,5253,5254,5257,5258,5259,5260,5261,5262,5263,5264,5265,5267,5268,5281,5282,5283,5284,
              5285,5286,5291,5293,5295,5299,5300,5302,5318,5303,5304,5305,5306,5307,5309,5310,5314,5315,5321,5322,5323,
              5325,5326,5327,5329,5331,5333,5334,5335,5336,5337,5341,5342,5343,5345,5346,5347,5350,5353,5355,5357,5360,
              5363,5371,5373,5374,5378,5379,5380,5381,5382,5384,5385,5387,5388,5392,5393,5394,5396,5397,5398,5399,5401,
              5402,5403,5404,5405,5406,5407,5408,5409,5410,5411,5412,5413,5414,5415,5416,5417,5418,5419,5420,5423,5427,
              5428,5430,5437,5440,5443,5444,5445,5447,5448,5449,5450,5451,5452,5453,5454,5455,5457,5458,5459,5460,5462,
              5463,5464,5470,5472,5473,5474,5475,5476,5480,5484,5486,5497,5498,5499,5501,5502,5503,5504,5505,5506,5507,
              5508,5513,5514,5515,5516,5517,5518,5519,5521,5522,5523,5524,5525,5527,5528,5529,5531,5532,5533,5534,5535,
              5536,5537,5538,5539,5541,5542,5545,5546,5547,5548,5549,5550,5551,5554,5555,5559,5560,5561,5563,5565,5566,
              5567,5568,5570,5574,5575,5576,5578,5580,5582,5583,5584,5585,5586,5587,5588,5589,5590,5593,5594,5596,5598,
              5600,5601,5604,5605,5610,5612,5614,5620,5626,5627,5628,5629,5630,5632,5635,5636,5637,5640,5641,5642,5643,
              5645,5646,5647,5649,5650,5652,5658,5659,5680,5682,5683,5685,5687,5690,5693,5694,5695,5696,5700,5701,5702,
              5705,5707,5708,5709,5710,5712,5713,5715,5716,5717,5718,5719,5721,5722,5723,5724,5725,5726,5727,5728,5729,
              5730,5731,5733,5734,5736,5741,5742,5743,5745,5746,5747,5748,5750,5751,5760,5763,5770,5773,5776,5777,5778,
              5779,5780,5781,5782,5783,5784,5785,5786,5787,5802,5803,5804,5805,5806,5807,5808,5809,5811,5812,5815,5816,
              5817,5821,5824,5825,5826,5829,5835,5836,5837,5838,5839,5845,5846,5847,5848,5849,5851,5852,5853,5854,5856,
              5857,5858,5859,5861,5862,5863,5868,5869,5871,5872,5873,5874,5876,5877,5878,5881,5882,5883,5884,5886,5888,
              5889,5892,5902,5903,5906,5911,5912,5913,5914,5915,5916,5917,5918,5931,5936,5937,5938,5939,5941,5943,5947,
              5948,5951,5953,5954,5955,5956,5957,5960,5961,5962,5966,5967,5970,5977,5978,5979,5981,5983,5984,5986,5987,
              5991,5993,5994,6139,6140,6141,6142,6143,6144,6146,6149,6700,6701,6704,6706,6707,6708,6710,6711,6713,6714,
              6715,6716,6717,6718,6719,6721,6723,6726,6727,6729,6730,6731,6734,6737,6740,6741,6750,6751,6761,6763,6770,
              6771,6775,6776,6777,6778,6779,6781,6782,6783,6784,6785,6788,6789,6791,6792,6793,6795,6796,6797,6798,6799,
              6800,6801,6806,6807,6812,6817,6818,6819,6821,6823,6825,6826,6827,6828,6829,6841,6843,6846,6847,6848,6851,
              6852,6853,6854,6855,6856,6857,6858,6859,6861,6863,6866,6868,6869,6870,6871,6872,6873,6875,6876,6877,6878,
              6879,6881,6882,6884,6885,6886,6887,6888,6889,6891,6893,6894,6895,6896,6898,6899,6900,6901,6902,6905,6907,
              6912,6914,6915,6916,6917,6918,6919,6921,6924,6926,6927,6928,6929,6940,6941,6942,6944,6946,6947,6949,6951,
              6953,6957,6958,6961,6962,6963,6964,6966,6967,6968,6969,6971,6973,6975,6977,6978,6980,6982,6983,6984,6985,
              6986,6987,6988,6991,6993,6995,6996,3844,4251,5681,5358,5308,5706,4345,4083,5248,4344,4374,4031,4371,3967]
    range3 = [6001,6002,6003,6004,6005,6006,6007,6008,6009,6010,6011,6012,6013,6014,6015,6016,6017,6018,6019,6020,6021,
              6022,6023,6024,6025,6026,6027,6028,6029,6030,6035,6036,6037,6039,6040,6050,6052,6055,6057,6058,6059,6060,
              6062,6063,6064,6065,6067,6069,6070,6076,6080,6082,6083,6084,6085,6087,6089,6090,6091,6092,6094,6095,6096,
              6098,6099,6100,6101,6102,6110,6120,6133,6150,6151,6153,6160,6165,6166,6170,6174,6183,6184,6190,6196,6200,
              6201,6210,6212,6213,6214,6215,6216,6217,6218,6220,6222,6224,6230,6238,6239,6240,6249,6250,6259,6260,6263,
              6264,6265,6270,6272,6280,6281,6282,6283,6285,6290,6292,6293,6294,6300,6301,6309,6310,6315,6320,6330,6335,
              6339,6350,6360,6363,6364,6386,6387,6390,6391,6392,6393,6394,6395,6396,6397,6398,6399,6400,6401,6402,6403,
              6404,6405,6406,6407,6408,6409,6411,6412,6413,6414,6415,6416,6418,6419,6421,6422,6425,6429,6430,6433,6440,
              6443,6444,6445,6447,6449,6450,6453,6454,6455,6456,6457,6460,6462,6470,6472,6475,6476,6480,6481,6483,6484,
              6486,6487,6488,6490,6493,6494,6499,6500,6501,6502,6503,6504,6505,6507,6508,6509,6510,6511,6512,6514,6515,
              6516,6517,6518,6520,6521,6523,6529,6530,6538,6539,6570,6571,6590,6600,6660,6601,6610,6611,6612,6613,6620,
              6622,6628,6629,6630,6631,6633,6636,6637,6638,6639,6640,6642,6643,6644,6645,6650,6652,6653,6655,6656,6657,
              6658,6659,6670,6674,6680,6683,6686,6687,6688,6689,6690,6693,6694,6697,6698,6699,7002,7003,7004,7005,7006,
              7007,7008,7009,7010,7011,7012,7013,7014,7015,7016,7018,7019,7020,7021,7022,7023,7024,7025,7026,7027,7028,
              7029,7030,7031,7032,7033,7034,7036,7037,7038,7039,7040,7041,7042,7043,7044,7045,7046,7047,7048,7049,7050,
              7051,7052,7053,7054,7056,7057,7058,7066,7070,7072,7074,7075,7078,7079,7080,7081,7082,7083,7084,7088,7089,
              7091,7092,7093,7097,7098,7099,7100,7101,7105,7110,7112,7113,7114,7119,7120,7121,7125,7127,7128,7129,7130,
              7140,7142,7150,7152,7153,7156,7159,7160,7165,7166,7167,7168,7169,7170,7176,7177,7178,7180,7190,7194,7200,
              7201,7203,7206,7211,7212,7213,7223,7224,7227,7228,7229,7231,7232,7234,7236,7238,7239,7240,7241,7242,7243,
              7246,7247,7250,7252,7255,7256,7257,7259,7260,7261,7263,7264,7266,7268,7270,7273,7280,7282,7284,7285,7286,
              7287,7288,7289,7290,7291,7295,7298,7300,7301,7310,7315,7316,7318,7319,7320,7321,7327,7329,7330,7331,7332,
              7333,7334,7335,7336,7338,7340,7341,7342,7343,7344,7345,7350,7351,7353,7354,7355,7357,7358,7359,7361,7366,
              7370,7372,7374,7380,7383,7384,7386,7387,7391,7392,7393,7397,7398,7399,7400,7401,7402,7403,7404,7405,7406,
              7407,7408,7409,7410,7411,7412,7413,7414,7415,7416,7417,7418,7419,7420,7421,7422,7423,7424,7425,7426,7427,
              7428,7429,7430,7431,7432,7433,7434,7435,7436,7437,7438,7439,7440,7441,7442,7443,7444,7445,7446,7447,7448,
              7449,7450,7451,7452,7453,7458,7459,7460,7462,7463,7464,7465,7466,7467,7468,7469,7471,7472,7473,7474,7475,
              7476,7477,7478,7479,7481,7483,7484,7485,7486,7488,7489,7491,7492,7493,7495,7496,7498,7499,7500,7501,7505,
              7506,7507,7509,7510,7512,7513,7514,7517,7519,7520,7525,7529,7530,7531,7533,7540,7541,7543,7549,7550,7551,
              7560,7562,7563,7566,7570,7580,7581,7584,7590,7591,7596,7600,7601,7619,7620,7622,7623,7624,7629,7630,7631,
              7632,7633,7634,7650,7651,7660,7663,7670,7671,7672,7690,7700,7701,7702,7703,7704,7705,7706,7707,7708,7709,
              7710,7711,7712,7713,7715,7716,7717,7718,7724,7725,7726,7728,7729,7730,7732,7734,7735,7736,7737,7738,7739,
              7740,7742,7744,7745,7746,7748,7750,7751,7760,7761,7770,7771,7777,7790,7791,7796,7797,7800,7801,7817,7818,
              7819,7820,7822,7855,7856,7860,7863,7864,7869,7870,7871,7882,7884,7890,7892,7893,7896,7898,7900,7901,7940,
              7944,7950,7960,7970,7971,7973,7976,7977,7980,7981,7982,7985,7990,7993,7994,8000,8001,8002,8003,8004,8005,
              8006,8007,8008,8009,8010,8011,8012,8013,8014,8015,8016,8019,8020,8021,8022,8023,8026,8027,8028,8029,8030,
              8031,8037,8038,8039,8041,8047,8048,8049,8050,8056,8058,8063,8064,8070,8071,8089,8091,8092,8093,8094,8095,
              8096,8097,8098,8099,8100,8102,8103,8108,8110,8114,8118,8120,8128,8130,8135,8136,8138,8140,8145,8146,8149,
              8150,8151,8157,8158,8159,8160,8161,8168,8170,8171,8178,8181,8182,8183,8184,8185,8186,8187,8188,8189,8190,
              8193,8195,8196,8197,8198,8200,8201,8205,8206,8210,8215,8220,8226,8230,8231,8232,8233,8250,8251,8255,8256,
              8260,8261,8264,8266,8270,8271,8273,8274,8275,8276,8281,8283,8285,8286,8288,8289,8290,8294,8297,8298,8300,
              8301,8305,8309,8310,8312,8313,8314,8315,8316,8320,8322,8323,8324,8325,8328,8340,8352,8360,8367,8370,8372,
              8373,8376,8377,8378,8380,8382,8384,8387,8388,8390,8392,8398,8400,8401,8405,8406,8407,8408,8409,8410,8412,
              8413,8414,8426,8428,8430,8432,8438,8439,8440,8445,8447,8448,8450,8455,8459,8465,8469,8470,8475,8480,8481,
              8483,8484,8485,8487,8488,8489,8493,8501,8502,8503,8504,8505,8506,8507,8508,8509,8510,8511,8512,8513,8514,
              8515,8516,8517,8520,8522,8523,8530,8531,8533,8534,8535,8536,8539,8540,8543,8545,8546,8550,8551,8581,8587,
              8590,8591,8600,8601,8602,8603,8604,8605,8606,8607,8608,8609,8610,8613,8614,8615,8616,8617,8618,8622,8624,
              8626,8629,8630,8633,8635,8638,8640,8641,8642,8643,8646,8647,8648,8650,8651,8654,8655,8656,8657,8658,8659,
              8661,8663,8664,8665,8672,8679,8680,8681,8686,8690,8691,8700,8701,8720,8723,8724,8725,8726,8730,8732,8733,
              8735,8740,8742,8743,8750,8752,8753,8762,8764,8766,8767,8770,8800,8801,8803,8805,8813,8820,8824,8826,8827,
              8830,8842,8843,8844,8850,8851,8852,8854,8860,8865,8870,8880,8883,8890,8891,8892,8900,8901,8905,8910,8920,
              8921,8960,8961,8976,8978,8980,8981,8985,9001,9002,9006,9007,9008,9009,9010,9011,9012,9013,9014,9015,9016,
              9017,9018,9019,9020,9022,9024,9027,9030,9034,9037,9038,9040,9042,9043,9046,9049,9050,9054,9055,9056,9057,
              9059,9060,9062,9064,9068,9069,9100,9103,9106,9107,9110,9118,9120,9128,9130,9131,9132,9134,9135,9136,9138,
              9140,9141,9143,9144,9146,9147,9148,9151,9152,9153,9156,9159,9161,9162,9163,9164,9169,9171,9180,9181,9182,
              9184,9185,9186,9189,9190,9192,9193,9194,9195,9197,9251,9252,9253,9254,9255,9256,9257,9258,9259,9260,9261,
              9262,9265,9266,9267,9268,9269,9270,9271,9272,9275,9276,9277,9278,9279,9280,9281,9283,9284,9285,9286,9288,
              9290,9291,9292,9293,9294,9295,9296,9297,9298,9299,9300,9302,9303,9304,9305,9310,9311,9315,9316,9321,9322,
              9325,9326,9327,9329,9334,9335,9336,9350,9355,9357,9358,9360,9365,9370,9372,9373,9380,9381,9385,9386,9388,
              9389,9392,9395,9400,9402,9403,9404,9405,9406,9407,9408,9409,9411,9414,9415,9419,9420,9423,9424,9425,9426,
              9427,9430,9436,9438,9439,9440,9441,9442,9443,9444,9445,9446,9450,9453,9454,9455,9465,9470,9475,9476,9477,
              9478,9479,9480,9481,9482,9483,9484,9485,9486,9487,9488,9489,9490,9491,9492,9493,9494,9495,9496,9497,9498,
              9501,9502,9503,9504,9505,9506,9507,9508,9509,9510,9511,9512,9513,9514,9515,9516,9517,9518,9519,9520,9521,
              9525,9526,9531,9532,9533,9536,9540,9545,9550,9551,9580,9582,9583,9584,9585,9586,9587,9590,9593,9595,9600,
              9609,9610,9613,9615,9616,9620,9621,9624,9650,9653,9657,9663,9664,9670,9672,9690,9691,9692,9700,9709,9710,
              9711,9712,9713,9714,9715,9716,9717,9722,9730,9733,9735,9740,9742,9750,9751,9755,9760,9763,9764,9765,9768,
              9770,9771,9772,9773,9775,9782,9783,9790,9800,9802,9810,9811,9815,9820,9826,9840,9845,9846,9900,9910,9912,
              9914,9915,9916,9917,9925,9930,9934,9935,9950,9951,9952,9960,9980,9981,9990,9991,6105,7873,8084,8907,8403,
              8393,9029,9104,9200,7606,7714,6522,7502,7653,8208,9119,9080,9000,7604,8802]

    mondelez = ''
    if (postnumber in range1) is True:
        mondelez = 1
    elif (postnumber in range2) is True:
        mondelez = 2
    elif (postnumber in range3) is True:
        mondelez = 3

    return mondelez

def or17(postnumber):
    or17Cond1 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 2665) & (postnumber <= 2669)) |
                 ((postnumber >= 6001) & (postnumber <= 6718)) | ((postnumber >= 6740) & (postnumber <= 6799)) |
                 ((postnumber >= 6821) & (postnumber <= 6829)) | ((postnumber >= 7002) & (postnumber <= 9991)))

    or17Cond2 = (((postnumber >= 275) & (postnumber <= 275)) | ((postnumber >= 277) & (postnumber <= 278)) |
                 ((postnumber >= 279) & (postnumber <= 279)) | ((postnumber >= 282) & (postnumber <= 286)) |
                 ((postnumber >= 363) & (postnumber <= 364)) | ((postnumber >= 366) & (postnumber <= 369)) |
                 ((postnumber >= 371) & (postnumber <= 371)) | ((postnumber >= 373) & (postnumber <= 376)) |
                 ((postnumber >= 378) & (postnumber <= 378)) | ((postnumber >= 381) & (postnumber <= 381)) |
                 ((postnumber >= 383) & (postnumber <= 383)) | ((postnumber >= 751) & (postnumber <= 751)) |
                 ((postnumber >= 753) & (postnumber <= 753)) | ((postnumber >= 757) & (postnumber <= 759)) |
                 ((postnumber >= 768) & (postnumber <= 768)) | ((postnumber >= 771) & (postnumber <= 771)) |
                 ((postnumber >= 773) & (postnumber <= 773)) | ((postnumber >= 775) & (postnumber <= 776)) |
                 ((postnumber >= 784) & (postnumber <= 784)) | ((postnumber >= 851) & (postnumber <= 851)) |
                 ((postnumber >= 855) & (postnumber <= 855)) | ((postnumber >= 858) & (postnumber <= 860)) |
                 ((postnumber >= 862) & (postnumber <= 862)) | ((postnumber >= 864) & (postnumber <= 864)) |
                 ((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3001) & (postnumber <= 3521)) |
                 ((postnumber >= 3524) & (postnumber <= 3526)) | ((postnumber >= 3529) & (postnumber <= 3999)) |
                 ((postnumber >= 4400) & (postnumber <= 4443)) | ((postnumber >= 4473) & (postnumber <= 4994)))

    or17Cond3 = (((postnumber >= 4001) & (postnumber <= 4395)) | ((postnumber >= 4460) & (postnumber <= 4465)) |
                 ((postnumber >= 5003) & (postnumber <= 5994)) | ((postnumber >= 6719) & (postnumber <= 6737)) |
                 ((postnumber >= 6800) & (postnumber <= 6819)) | ((postnumber >= 6841) & (postnumber <= 6996)))

    or17Cond4 = (((postnumber >= 10) & (postnumber <= 274)) | ((postnumber >= 276) & (postnumber <= 276)) |
                 ((postnumber >= 280) & (postnumber <= 281)) | ((postnumber >= 287) & (postnumber <= 362)) |
                 ((postnumber >= 365) & (postnumber <= 365)) | ((postnumber >= 370) & (postnumber <= 370)) |
                 ((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 377) & (postnumber <= 377)) |
                 ((postnumber >= 379) & (postnumber <= 380)) | ((postnumber >= 382) & (postnumber <= 382)) |
                 ((postnumber >= 401) & (postnumber <= 750)) | ((postnumber >= 752) & (postnumber <= 752)) |
                 ((postnumber >= 754) & (postnumber <= 756)) | ((postnumber >= 761) & (postnumber <= 767)) |
                 ((postnumber >= 770) & (postnumber <= 770)) | ((postnumber >= 772) & (postnumber <= 772)) |
                 ((postnumber >= 774) & (postnumber <= 774)) | ((postnumber >= 777) & (postnumber <= 783)) |
                 ((postnumber >= 785) & (postnumber <= 850)) | ((postnumber >= 852) & (postnumber <= 854)) |
                 ((postnumber >= 856) & (postnumber <= 857)) | ((postnumber >= 861) & (postnumber <= 861)) |
                 ((postnumber >= 863) & (postnumber <= 863)) | ((postnumber >= 870) & (postnumber <= 1295)) |
                 ((postnumber >= 1400) & (postnumber <= 2487)) | ((postnumber >= 2600) & (postnumber <= 2663)) |
                 ((postnumber >= 2670) & (postnumber <= 2985)) | ((postnumber >= 3522) & (postnumber <= 3522)) |
                 ((postnumber >= 3528) & (postnumber <= 3528)))


    conditionList = [or17Cond1, or17Cond2, or17Cond3, or17Cond4]

    def conditioncheck(conditions):
        or17 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                or17 = index + 1
        return or17

    or17 = conditioncheck(conditionList)

    return or17

def or18(postnumber):
    or18Cond1 = (((postnumber >= 4400) & (postnumber <= 4443)) | ((postnumber >= 4473) & (postnumber <= 4994)))

    or18Cond2 = (((postnumber >= 5003) & (postnumber <= 5399)) | ((postnumber >= 5600) & (postnumber <= 5620)) |
                 ((postnumber >= 5630) & (postnumber <= 5632)) | ((postnumber >= 5640) & (postnumber <= 5748)) |
                 ((postnumber >= 5802) & (postnumber <= 5994)) | ((postnumber >= 6719) & (postnumber <= 6737)) |
                 ((postnumber >= 6800) & (postnumber <= 6819)) | ((postnumber >= 6841) & (postnumber <= 6996)))

    or18Cond3 = (((postnumber >= 1371) & (postnumber <= 1397)) | ((postnumber >= 3001) & (postnumber <= 3100)) |
                 ((postnumber >= 3300) & (postnumber <= 3521)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                 ((postnumber >= 3529) & (postnumber <= 3595)) | ((postnumber >= 3620) & (postnumber <= 3632)))

    or18Cond4 = (((postnumber >= 4198) & (postnumber <= 4299)) | ((postnumber >= 5401) & (postnumber <= 5598)) |
                 ((postnumber >= 5626) & (postnumber <= 5629)) | ((postnumber >= 5635) & (postnumber <= 5637)) |
                 ((postnumber >= 5750) & (postnumber <= 5787)))

    or18Cond5 = (((postnumber >= 2090) & (postnumber <= 2091)) | ((postnumber >= 2201) & (postnumber <= 2219)) |
                 ((postnumber >= 2224) & (postnumber <= 2226)) | ((postnumber >= 2256) & (postnumber <= 2487)) |
                 ((postnumber >= 2601) & (postnumber <= 2663)) | ((postnumber >= 2670) & (postnumber <= 2712)) |
                 ((postnumber >= 2714) & (postnumber <= 2714)) | ((postnumber >= 2750) & (postnumber <= 2985)) |
                 ((postnumber >= 3522) & (postnumber <= 3522)) | ((postnumber >= 3528) & (postnumber <= 3528)))

    or18Cond6 = (((postnumber >= 2665) & (postnumber <= 2669)) | ((postnumber >= 6001) & (postnumber <= 6571)) |
                 ((postnumber >= 6600) & (postnumber <= 6674)) | ((postnumber >= 6700) & (postnumber <= 6718)) |
                 ((postnumber >= 6740) & (postnumber <= 6799)) | ((postnumber >= 6821) & (postnumber <= 6829)))

    or18Cond7 = (((postnumber >= 7980) & (postnumber <= 7982)) | ((postnumber >= 8000) & (postnumber <= 8408)) |
                 ((postnumber >= 8410) & (postnumber <= 9002)))

    or18Cond8 = (((postnumber >= 275) & (postnumber <= 275)) | ((postnumber >= 277) & (postnumber <= 278)) |
                 ((postnumber >= 279) & (postnumber <= 279)) | ((postnumber >= 282) & (postnumber <= 286)) |
                 ((postnumber >= 363) & (postnumber <= 364)) | ((postnumber >= 366) & (postnumber <= 369)) |
                 ((postnumber >= 371) & (postnumber <= 371)) | ((postnumber >= 373) & (postnumber <= 376)) |
                 ((postnumber >= 378) & (postnumber <= 378)) | ((postnumber >= 381) & (postnumber <= 381)) |
                 ((postnumber >= 383) & (postnumber <= 383)) | ((postnumber >= 751) & (postnumber <= 751)) |
                 ((postnumber >= 753) & (postnumber <= 753)) | ((postnumber >= 757) & (postnumber <= 758)) |
                 ((postnumber >= 768) & (postnumber <= 768)) | ((postnumber >= 771) & (postnumber <= 771)) |
                 ((postnumber >= 773) & (postnumber <= 773)) | ((postnumber >= 775) & (postnumber <= 776)) |
                 ((postnumber >= 784) & (postnumber <= 784)) | ((postnumber >= 851) & (postnumber <= 851)) |
                 ((postnumber >= 855) & (postnumber <= 855)) | ((postnumber >= 858) & (postnumber <= 860)) |
                 ((postnumber >= 862) & (postnumber <= 862)) | ((postnumber >= 864) & (postnumber <= 864)) |
                 ((postnumber >= 1300) & (postnumber <= 1369)))

    or18Cond9 = (((postnumber >= 10) & (postnumber <= 274)) | ((postnumber >= 276) & (postnumber <= 276)) |
                 ((postnumber >= 280) & (postnumber <= 281)) | ((postnumber >= 287) & (postnumber <= 362)) |
                 ((postnumber >= 365) & (postnumber <= 365)) | ((postnumber >= 370) & (postnumber <= 370)) |
                 ((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 377) & (postnumber <= 377)) |
                 ((postnumber >= 379) & (postnumber <= 380)) | ((postnumber >= 382) & (postnumber <= 382)) |
                 ((postnumber >= 401) & (postnumber <= 750)) | ((postnumber >= 752) & (postnumber <= 752)) |
                 ((postnumber >= 754) & (postnumber <= 756)) | ((postnumber >= 759) & (postnumber <= 767)) |
                 ((postnumber >= 770) & (postnumber <= 770)) | ((postnumber >= 772) & (postnumber <= 772)) |
                 ((postnumber >= 774) & (postnumber <= 774)) | ((postnumber >= 777) & (postnumber <= 783)) |
                 ((postnumber >= 785) & (postnumber <= 850)) | ((postnumber >= 852) & (postnumber <= 854)) |
                 ((postnumber >= 856) & (postnumber <= 857)) | ((postnumber >= 861) & (postnumber <= 861)) |
                 ((postnumber >= 863) & (postnumber <= 863)) | ((postnumber >= 870) & (postnumber <= 1295)))

    or18Cond10 = (((postnumber >= 1470) & (postnumber <= 1488)) | ((postnumber >= 1900) & (postnumber <= 1910)) |
                  ((postnumber >= 1920) & (postnumber <= 1945)) | ((postnumber >= 1954) & (postnumber <= 2081)) |
                  ((postnumber >= 2092) & (postnumber <= 2170)) | ((postnumber >= 2220) & (postnumber <= 2223)) |
                  ((postnumber >= 2230) & (postnumber <= 2240)) | ((postnumber >= 2713) & (postnumber <= 2713)) |
                  ((postnumber >= 2715) & (postnumber <= 2743)))

    or18Cond11 = (((postnumber >= 4001) & (postnumber <= 4187)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                  ((postnumber >= 4460) & (postnumber <= 4465)))

    or18Cond12 = (((postnumber >= 8409) & (postnumber <= 8409)) | ((postnumber >= 9006) & (postnumber <= 9991)))

    or18Cond13 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 6590) & (postnumber <= 6590)) |
                  ((postnumber >= 6680) & (postnumber <= 6699)) | ((postnumber >= 7002) & (postnumber <= 7977)) |
                  ((postnumber >= 7985) & (postnumber <= 7994)))

    or18Cond14 = (((postnumber >= 3101) & (postnumber <= 3296)) | ((postnumber >= 3601) & (postnumber <= 3619)) |
                  ((postnumber >= 3646) & (postnumber <= 3999)))

    or18Cond15 = (((postnumber >= 1400) & (postnumber <= 1458)) | ((postnumber >= 1501) & (postnumber <= 1892)) |
                  ((postnumber >= 1911) & (postnumber <= 1914)) | ((postnumber >= 1950) & (postnumber <= 1950)))

    conditionList = [or18Cond1, or18Cond2, or18Cond3, or18Cond4, or18Cond5, or18Cond6, or18Cond7, or18Cond8,
                     or18Cond9, or18Cond10, or18Cond11, or18Cond12, or18Cond13, or18Cond14, or18Cond15]

    def conditioncheck(conditions):
        or18 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                or18 = index + 1
        return or18

    or18 = conditioncheck(conditionList)

    return or18

def ork2(postnumber):
    ork2Cond1 = (((postnumber >= 4400) & (postnumber <= 4443)) | ((postnumber >= 4473) & (postnumber <= 4994)))

    ork2Cond2 = (((postnumber >= 5003) & (postnumber <= 5399)) | ((postnumber >= 5600) & (postnumber <= 5620)) |
                  ((postnumber >= 5630) & (postnumber <= 5632)) | ((postnumber >= 5640) & (postnumber <= 5748)) |
                  ((postnumber >= 5802) & (postnumber <= 5994)) | ((postnumber >= 6719) & (postnumber <= 6737)) |
                  ((postnumber >= 6800) & (postnumber <= 6819)) | ((postnumber >= 6841) & (postnumber <= 6996)))

    ork2Cond3 = (((postnumber >= 1371) & (postnumber <= 1397)) | ((postnumber >= 3001) & (postnumber <= 3100)) |
                  ((postnumber >= 3300) & (postnumber <= 3521)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                  ((postnumber >= 3529) & (postnumber <= 3595)) | ((postnumber >= 3620) & (postnumber <= 3632)))

    ork2Cond4 = (((postnumber >= 4198) & (postnumber <= 4299)) | ((postnumber >= 5401) & (postnumber <= 5598)) |
                  ((postnumber >= 5626) & (postnumber <= 5629)) | ((postnumber >= 5635) & (postnumber <= 5637)) |
                  ((postnumber >= 5750) & (postnumber <= 5787)))

    ork2Cond5 = (((postnumber >= 2090) & (postnumber <= 2091)) | ((postnumber >= 2201) & (postnumber <= 2219)) |
                  ((postnumber >= 2224) & (postnumber <= 2226)) | ((postnumber >= 2256) & (postnumber <= 2487)) |
                  ((postnumber >= 2601) & (postnumber <= 2663)) | ((postnumber >= 2670) & (postnumber <= 2712)) |
                  ((postnumber >= 2714) & (postnumber <= 2714)) | ((postnumber >= 2750) & (postnumber <= 2985)) |
                  ((postnumber >= 3522) & (postnumber <= 3522)) | ((postnumber >= 3528) & (postnumber <= 3528)))

    ork2Cond6 = (((postnumber >= 2665) & (postnumber <= 2669)) | ((postnumber >= 6001) & (postnumber <= 6571)) |
                  ((postnumber >= 6600) & (postnumber <= 6674)) | ((postnumber >= 6700) & (postnumber <= 6718)) |
                  ((postnumber >= 6740) & (postnumber <= 6799)) | ((postnumber >= 6821) & (postnumber <= 6829)))

    ork2Cond7 = (((postnumber >= 7980) & (postnumber <= 7982)) | ((postnumber >= 8000) & (postnumber <= 8408)) |
                  ((postnumber >= 8410) & (postnumber <= 9002)))

    ork2Cond8 = (((postnumber >= 275) & (postnumber <= 275)) | ((postnumber >= 277) & (postnumber <= 279)) |
                  ((postnumber >= 282) & (postnumber <= 286)) | ((postnumber >= 363) & (postnumber <= 364)) |
                  ((postnumber >= 366) & (postnumber <= 369)) | ((postnumber >= 371) & (postnumber <= 371)) |
                  ((postnumber >= 373) & (postnumber <= 376)) | ((postnumber >= 378) & (postnumber <= 378)) |
                  ((postnumber >= 381) & (postnumber <= 381)) | ((postnumber >= 383) & (postnumber <= 383)) |
                  ((postnumber >= 751) & (postnumber <= 751)) | ((postnumber >= 753) & (postnumber <= 753)) |
                  ((postnumber >= 757) & (postnumber <= 758)) | ((postnumber >= 768) & (postnumber <= 768)) |
                  ((postnumber >= 771) & (postnumber <= 771)) | ((postnumber >= 773) & (postnumber <= 773)) |
                  ((postnumber >= 775) & (postnumber <= 776)) | ((postnumber >= 784) & (postnumber <= 784)) |
                  ((postnumber >= 851) & (postnumber <= 851)) | ((postnumber >= 855) & (postnumber <= 855)) |
                  ((postnumber >= 858) & (postnumber <= 860)) | ((postnumber >= 862) & (postnumber <= 862)) |
                  ((postnumber >= 864) & (postnumber <= 864)) | ((postnumber >= 1300) & (postnumber <= 1369)))

    ork2Cond9 = (((postnumber >= 10) & (postnumber <= 274)) | ((postnumber >= 276) & (postnumber <= 276)) |
                  ((postnumber >= 280) & (postnumber <= 281)) | ((postnumber >= 287) & (postnumber <= 362)) |
                  ((postnumber >= 365) & (postnumber <= 365)) | ((postnumber >= 370) & (postnumber <= 370)) |
                  ((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 377) & (postnumber <= 377)) |
                  ((postnumber >= 379) & (postnumber <= 380)) | ((postnumber >= 382) & (postnumber <= 382)) |
                  ((postnumber >= 401) & (postnumber <= 750)) | ((postnumber >= 752) & (postnumber <= 752)) |
                  ((postnumber >= 754) & (postnumber <= 756)) | ((postnumber >= 759) & (postnumber <= 767)) |
                  ((postnumber >= 770) & (postnumber <= 770)) | ((postnumber >= 772) & (postnumber <= 772)) |
                  ((postnumber >= 774) & (postnumber <= 774)) | ((postnumber >= 777) & (postnumber <= 783)) |
                  ((postnumber >= 785) & (postnumber <= 850)) | ((postnumber >= 852) & (postnumber <= 854)) |
                  ((postnumber >= 856) & (postnumber <= 857)) | ((postnumber >= 861) & (postnumber <= 861)) |
                  ((postnumber >= 863) & (postnumber <= 863)) | ((postnumber >= 870) & (postnumber <= 1295)))

    ork2Cond10 = (((postnumber >= 1470) & (postnumber <= 1488)) | ((postnumber >= 1900) & (postnumber <= 1910)) |
                   ((postnumber >= 1920) & (postnumber <= 1945)) | ((postnumber >= 1954) & (postnumber <= 2081)) |
                   ((postnumber >= 2092) & (postnumber <= 2170)) | ((postnumber >= 2220) & (postnumber <= 2223)) |
                   ((postnumber >= 2230) & (postnumber <= 2240)) | ((postnumber >= 2713) & (postnumber <= 2713)) |
                   ((postnumber >= 2715) & (postnumber <= 2743)))

    ork2Cond11 = (((postnumber >= 4001) & (postnumber <= 4187)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                   ((postnumber >= 4460) & (postnumber <= 4465)))

    ork2Cond12 = (((postnumber >= 8409) & (postnumber <= 8409)) | ((postnumber >= 9006) & (postnumber <= 9991)))

    ork2Cond13 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 6590) & (postnumber <= 6590)) |
                  ((postnumber >= 6680) & (postnumber <= 6699)) | ((postnumber >= 7002) & (postnumber <= 7977)) |
                  ((postnumber >= 7985) & (postnumber <= 7994)))

    ork2Cond14 = (((postnumber >= 3101) & (postnumber <= 3296)) | ((postnumber >= 3601) & (postnumber <= 3619)) |
                  ((postnumber >= 3646) & (postnumber <= 3999)))

    ork2Cond15 = (((postnumber >= 1400) & (postnumber <= 1458)) | ((postnumber >= 1501) & (postnumber <= 1892)) |
                   ((postnumber >= 1911) & (postnumber <= 1914)) | ((postnumber >= 1950) & (postnumber <= 1950)))

    conditionList = [ork2Cond1, ork2Cond2, ork2Cond3, ork2Cond4, ork2Cond5, ork2Cond6, ork2Cond7, ork2Cond8,
                     ork2Cond9, ork2Cond10, ork2Cond11, ork2Cond12, ork2Cond13, ork2Cond14, ork2Cond15]

    def conditioncheck(conditions):
        ork2 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                ork2 = index + 1
        return ork2

    ork2 = conditioncheck(conditionList)

    return ork2

def ork3(postnumber):
    ork3Cond1 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 2665) & (postnumber <= 2669)) |
                 ((postnumber >= 6001) & (postnumber <= 6718)) | ((postnumber >= 6740) & (postnumber <= 6799)) |
                 ((postnumber >= 6821) & (postnumber <= 6829)) | ((postnumber >= 7002) & (postnumber <= 9991)))

    ork3Cond2 = (((postnumber >= 275) & (postnumber <= 275)) | ((postnumber >= 277) & (postnumber <= 279)) |
                 ((postnumber >= 282) & (postnumber <= 286)) | ((postnumber >= 363) & (postnumber <= 364)) |
                 ((postnumber >= 366) & (postnumber <= 369)) | ((postnumber >= 371) & (postnumber <= 371)) |
                 ((postnumber >= 373) & (postnumber <= 376)) | ((postnumber >= 378) & (postnumber <= 378)) |
                 ((postnumber >= 381) & (postnumber <= 381)) | ((postnumber >= 383) & (postnumber <= 383)) |
                 ((postnumber >= 751) & (postnumber <= 751)) | ((postnumber >= 753) & (postnumber <= 753)) |
                 ((postnumber >= 757) & (postnumber <= 759)) | ((postnumber >= 768) & (postnumber <= 768)) |
                 ((postnumber >= 771) & (postnumber <= 771)) | ((postnumber >= 773) & (postnumber <= 773)) |
                 ((postnumber >= 775) & (postnumber <= 776)) | ((postnumber >= 784) & (postnumber <= 784)) |
                 ((postnumber >= 851) & (postnumber <= 851)) | ((postnumber >= 855) & (postnumber <= 855)) |
                 ((postnumber >= 858) & (postnumber <= 860)) | ((postnumber >= 862) & (postnumber <= 862)) |
                 ((postnumber >= 864) & (postnumber <= 864)) | ((postnumber >= 1300) & (postnumber <= 1397)) |
                 ((postnumber >= 3001) & (postnumber <= 3521)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                 ((postnumber >= 3529) & (postnumber <= 3999)) | ((postnumber >= 4400) & (postnumber <= 4443)) |
                 ((postnumber >= 4473) & (postnumber <= 4994)))

    ork3Cond3 = (((postnumber >= 4001) & (postnumber <= 4395)) | ((postnumber >= 4460) & (postnumber <= 4465)) |
                 ((postnumber >= 5003) & (postnumber <= 5994)) | ((postnumber >= 6719) & (postnumber <= 6737)) |
                 ((postnumber >= 6800) & (postnumber <= 6819)) | ((postnumber >= 6841) & (postnumber <= 6996)))

    ork3Cond4 = (((postnumber >= 10) & (postnumber <= 274)) | ((postnumber >= 276) & (postnumber <= 276)) |
                 ((postnumber >= 280) & (postnumber <= 281)) | ((postnumber >= 287) & (postnumber <= 362)) |
                 ((postnumber >= 365) & (postnumber <= 365)) | ((postnumber >= 370) & (postnumber <= 370)) |
                 ((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 377) & (postnumber <= 377)) |
                 ((postnumber >= 379) & (postnumber <= 380)) | ((postnumber >= 382) & (postnumber <= 382)) |
                 ((postnumber >= 401) & (postnumber <= 750)) | ((postnumber >= 752) & (postnumber <= 752)) |
                 ((postnumber >= 754) & (postnumber <= 756)) | ((postnumber >= 764) & (postnumber <= 767)) |
                 ((postnumber >= 770) & (postnumber <= 770)) | ((postnumber >= 772) & (postnumber <= 772)) |
                 ((postnumber >= 774) & (postnumber <= 774)) | ((postnumber >= 777) & (postnumber <= 783)) |
                 ((postnumber >= 785) & (postnumber <= 850)) | ((postnumber >= 852) & (postnumber <= 854)) |
                 ((postnumber >= 856) & (postnumber <= 857)) | ((postnumber >= 861) & (postnumber <= 861)) |
                 ((postnumber >= 863) & (postnumber <= 863)) | ((postnumber >= 870) & (postnumber <= 1295)) |
                 ((postnumber >= 1400) & (postnumber <= 2487)) | ((postnumber >= 2601) & (postnumber <= 2663)) |
                 ((postnumber >= 2670) & (postnumber <= 2985)) | ((postnumber >= 3522) & (postnumber <= 3522)) |
                 ((postnumber >= 3528) & (postnumber <= 3528)))

    conditionList = [ork3Cond1, ork3Cond2, ork3Cond3, ork3Cond4]

    def conditioncheck(conditions):
        ork3 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                ork3 = index + 1
        return ork3

    ork3 = conditioncheck(conditionList)

    return ork3

def reb1(postnumber):
    reb1Cond1 = (((postnumber >= 139) & (postnumber <= 139)) | ((postnumber >= 198) & (postnumber <= 198)) |
                 ((postnumber >= 679) & (postnumber <= 694)) | ((postnumber >= 1101) & (postnumber <= 1295)) |
                 ((postnumber >= 1400) & (postnumber <= 1459)) | ((postnumber >= 1501) & (postnumber <= 1892)) |
                 ((postnumber >= 1912) & (postnumber <= 1914)) | ((postnumber >= 1960) & (postnumber <= 1960)))

    reb1Cond2 = (((postnumber >= 1471) & (postnumber <= 1480)) | ((postnumber >= 1900) & (postnumber <= 1911)) |
                 ((postnumber >= 1920) & (postnumber <= 1954)) | ((postnumber >= 1963) & (postnumber <= 2695)) |
                 ((postnumber >= 2760) & (postnumber <= 2760)) | ((postnumber >= 2801) & (postnumber <= 2868)) |
                 ((postnumber >= 2881) & (postnumber <= 2882)) | ((postnumber >= 2893) & (postnumber <= 2893)) |
                 ((postnumber >= 2901) & (postnumber <= 2907)) | ((postnumber >= 2917) & (postnumber <= 2917)) |
                 ((postnumber >= 2929) & (postnumber <= 2929)) | ((postnumber >= 2936) & (postnumber <= 2936)) |
                 ((postnumber >= 2939) & (postnumber <= 2939)) | ((postnumber >= 2950) & (postnumber <= 2952)) |
                 ((postnumber >= 2959) & (postnumber <= 2959)) | ((postnumber >= 2967) & (postnumber <= 2967)) |
                 ((postnumber >= 2977) & (postnumber <= 2977)))

    reb1Cond3 = (((postnumber >= 10) & (postnumber <= 137)) | ((postnumber >= 150) & (postnumber <= 167)) |
                 ((postnumber >= 169) & (postnumber <= 196)) | ((postnumber >= 445) & (postnumber <= 445)) |
                 ((postnumber >= 454) & (postnumber <= 678)) | ((postnumber >= 758) & (postnumber <= 764)) |
                 ((postnumber >= 858) & (postnumber <= 864)) | ((postnumber >= 871) & (postnumber <= 875)) |
                 ((postnumber >= 877) & (postnumber <= 1089)) | ((postnumber >= 1470) & (postnumber <= 1470)) |
                 ((postnumber >= 1481) & (postnumber <= 1488)) | ((postnumber >= 2711) & (postnumber <= 2750)) |
                 ((postnumber >= 2770) & (postnumber <= 2770)))

    reb1Cond4 = (((postnumber >= 1300) & (postnumber <= 1341)) | ((postnumber >= 1346) & (postnumber <= 1349)) |
                 ((postnumber >= 1351) & (postnumber <= 1352)) | ((postnumber >= 1370) & (postnumber <= 1397)) |
                 ((postnumber >= 2870) & (postnumber <= 2880)) | ((postnumber >= 2890) & (postnumber <= 2890)) |
                 ((postnumber >= 2900) & (postnumber <= 2900)) | ((postnumber >= 2910) & (postnumber <= 2910)) |
                 ((postnumber >= 2918) & (postnumber <= 2923)) | ((postnumber >= 2930) & (postnumber <= 2933)) |
                 ((postnumber >= 2937) & (postnumber <= 2937)) | ((postnumber >= 2940) & (postnumber <= 2943)) |
                 ((postnumber >= 2953) & (postnumber <= 2953)) | ((postnumber >= 2960) & (postnumber <= 2966)) |
                 ((postnumber >= 2973) & (postnumber <= 2975)) | ((postnumber >= 2985) & (postnumber <= 3060)) |
                 ((postnumber >= 3070) & (postnumber <= 3070)) | ((postnumber >= 3075) & (postnumber <= 3075)) |
                 ((postnumber >= 3090) & (postnumber <= 3092)) | ((postnumber >= 3300) & (postnumber <= 3648)) |
                 ((postnumber >= 4604) & (postnumber <= 4639)) | ((postnumber >= 4656) & (postnumber <= 4720)) |
                 ((postnumber >= 4760) & (postnumber <= 4760)) | ((postnumber >= 4770) & (postnumber <= 4770)) |
                 ((postnumber >= 4790) & (postnumber <= 4790)) | ((postnumber >= 4888) & (postnumber <= 4888)))

    reb1Cond5 = (((postnumber >= 3061) & (postnumber <= 3061)) | ((postnumber >= 3071) & (postnumber <= 3071)) |
                 ((postnumber >= 3080) & (postnumber <= 3089)) | ((postnumber >= 3095) & (postnumber <= 3296)) |
                 ((postnumber >= 3650) & (postnumber <= 3999)) | ((postnumber >= 4724) & (postnumber <= 4755)) |
                 ((postnumber >= 4766) & (postnumber <= 4768)) | ((postnumber >= 4780) & (postnumber <= 4780)) |
                 ((postnumber >= 4791) & (postnumber <= 4887)) | ((postnumber >= 4889) & (postnumber <= 4994)))

    reb1Cond6 = (((postnumber >= 4001) & (postnumber <= 4596)) | ((postnumber >= 4640) & (postnumber <= 4647)) |
                 ((postnumber >= 5235) & (postnumber <= 5235)) | ((postnumber >= 5499) & (postnumber <= 5593)) |
                 ((postnumber >= 5596) & (postnumber <= 5596)))

    reb1Cond7 = (((postnumber >= 5003) & (postnumber <= 5232)) | ((postnumber >= 5236) & (postnumber <= 5498)) |
                 ((postnumber >= 5594) & (postnumber <= 5595)) | ((postnumber >= 5598) & (postnumber <= 5736)) |
                 ((postnumber >= 5750) & (postnumber <= 5957)) | ((postnumber >= 5981) & (postnumber <= 5983)) |
                 ((postnumber >= 5986) & (postnumber <= 5986)) | ((postnumber >= 5993) & (postnumber <= 5993)))

    reb1Cond8 = (((postnumber >= 7002) & (postnumber <= 7977)) | ((postnumber >= 7981) & (postnumber <= 7981)) |
                 ((postnumber >= 7985) & (postnumber <= 7994)))

    reb1Cond9 = (((postnumber >= 168) & (postnumber <= 168)) | ((postnumber >= 201) & (postnumber <= 444)) |
                 ((postnumber >= 450) & (postnumber <= 452)) | ((postnumber >= 701) & (postnumber <= 757)) |
                 ((postnumber >= 765) & (postnumber <= 857)) | ((postnumber >= 870) & (postnumber <= 870)) |
                 ((postnumber >= 876) & (postnumber <= 876)) | ((postnumber >= 1344) & (postnumber <= 1344)) |
                 ((postnumber >= 1350) & (postnumber <= 1350)) | ((postnumber >= 1353) & (postnumber <= 1369)) |
                 ((postnumber >= 5741) & (postnumber <= 5748)) | ((postnumber >= 5960) & (postnumber <= 5979)) |
                 ((postnumber >= 5984) & (postnumber <= 5984)) | ((postnumber >= 5987) & (postnumber <= 5991)) |
                 ((postnumber >= 5994) & (postnumber <= 6996)) | ((postnumber >= 7980) & (postnumber <= 7980)) |
                 ((postnumber >= 7982) & (postnumber <= 7982)) | ((postnumber >= 8000) & (postnumber <= 9991)))

    conditionList = [reb1Cond1, reb1Cond2, reb1Cond3, reb1Cond4, reb1Cond5, reb1Cond6, reb1Cond7, reb1Cond8, reb1Cond9]

    def conditioncheck(conditions):
        reb1 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                reb1 = index + 1
        return reb1

    reb1 = conditioncheck(conditionList)

    return reb1

def rin3(postnumber):
    rin3Cond1 = (((postnumber >= 1501) & (postnumber <= 1539)) | ((postnumber >= 1560) & (postnumber <= 1798)) |
                 ((postnumber >= 1825) & (postnumber <= 1825)) | ((postnumber >= 1832) & (postnumber <= 1832)))

    rin3Cond2 = (((postnumber >= 1471) & (postnumber <= 1488)) | ((postnumber >= 1800) & (postnumber <= 1808)) |
                 ((postnumber >= 1812) & (postnumber <= 1814)) | ((postnumber >= 1831) & (postnumber <= 1831)) |
                 ((postnumber >= 1851) & (postnumber <= 1851)) | ((postnumber >= 1861) & (postnumber <= 1861)) |
                 ((postnumber >= 1871) & (postnumber <= 1880)) | ((postnumber >= 1891) & (postnumber <= 1891)) |
                 ((postnumber >= 1900) & (postnumber <= 1910)) | ((postnumber >= 1920) & (postnumber <= 2093)) |
                 ((postnumber >= 2150) & (postnumber <= 2170)) | ((postnumber >= 2711) & (postnumber <= 2770)) |
                 ((postnumber >= 3520) & (postnumber <= 3522)))

    rin3Cond3 = (((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3430) & (postnumber <= 3474)) |
                 ((postnumber >= 3477) & (postnumber <= 3478)))

    rin3Cond4 = ((postnumber >= 4724) & (postnumber <= 4994))

    rin3Cond5 = (((postnumber >= 3001) & (postnumber <= 3075)) | ((postnumber >= 3090) & (postnumber <= 3095)) |
                 ((postnumber >= 3300) & (postnumber <= 3428)) | ((postnumber >= 3475) & (postnumber <= 3476)) |
                 ((postnumber >= 3480) & (postnumber <= 3519)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                 ((postnumber >= 3529) & (postnumber <= 3538)) | ((postnumber >= 3541) & (postnumber <= 3541)) |
                 ((postnumber >= 3544) & (postnumber <= 3544)) | ((postnumber >= 3551) & (postnumber <= 3551)) |
                 ((postnumber >= 3561) & (postnumber <= 3561)) | ((postnumber >= 3571) & (postnumber <= 3576)) |
                 ((postnumber >= 3581) & (postnumber <= 3581)) | ((postnumber >= 3601) & (postnumber <= 3648)))

    rin3Cond6 = (((postnumber >= 9186) & (postnumber <= 9186)) | ((postnumber >= 9501) & (postnumber <= 9991)))

    rin3Cond7 = (((postnumber >= 1400) & (postnumber <= 1470)) | ((postnumber >= 1540) & (postnumber <= 1556)) |
                 ((postnumber >= 1809) & (postnumber <= 1811)) | ((postnumber >= 1815) & (postnumber <= 1823)) |
                 ((postnumber >= 1827) & (postnumber <= 1830)) | ((postnumber >= 1850) & (postnumber <= 1850)) |
                 ((postnumber >= 1859) & (postnumber <= 1860)) | ((postnumber >= 1866) & (postnumber <= 1870)) |
                 ((postnumber >= 1890) & (postnumber <= 1890)) | ((postnumber >= 1892) & (postnumber <= 1892)) |
                 ((postnumber >= 1911) & (postnumber <= 1914)))

    rin3Cond8 = (((postnumber >= 2100) & (postnumber <= 2134)) | ((postnumber >= 2200) & (postnumber <= 2283)) |
                 ((postnumber >= 2312) & (postnumber <= 2318)) | ((postnumber >= 2320) & (postnumber <= 2322)) |
                 ((postnumber >= 2324) & (postnumber <= 2324)) | ((postnumber >= 2330) & (postnumber <= 2337)) |
                 ((postnumber >= 2340) & (postnumber <= 2353)) | ((postnumber >= 2360) & (postnumber <= 2364)) |
                 ((postnumber >= 2372) & (postnumber <= 2381)) | ((postnumber >= 2390) & (postnumber <= 2390)) |
                 ((postnumber >= 2401) & (postnumber <= 2487)) | ((postnumber >= 2610) & (postnumber <= 2610)) |
                 ((postnumber >= 2612) & (postnumber <= 2612)))

    rin3Cond9 = (((postnumber >= 3596) & (postnumber <= 3599)) | ((postnumber >= 5003) & (postnumber <= 5499)) |
                 ((postnumber >= 5550) & (postnumber <= 5559)) | ((postnumber >= 5590) & (postnumber <= 5715)) |
                 ((postnumber >= 5719) & (postnumber <= 5736)) | ((postnumber >= 5750) & (postnumber <= 5957)) |
                 ((postnumber >= 5981) & (postnumber <= 5994)))

    rin3Cond10 = ((postnumber >= 6001) & (postnumber <= 6699))

    rin3Cond11 = (((postnumber >= 8000) & (postnumber <= 8892)) | ((postnumber >= 8976) & (postnumber <= 8985)) |
                  ((postnumber >= 9304) & (postnumber <= 9304)) | ((postnumber >= 9392) & (postnumber <= 9392)) |
                  ((postnumber >= 9436) & (postnumber <= 9436)) | ((postnumber >= 9439) & (postnumber <= 9455)) |
                  ((postnumber >= 9470) & (postnumber <= 9476)))

    rin3Cond12 = (((postnumber >= 7180) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7533)) |
                  ((postnumber >= 7550) & (postnumber <= 7994)) | ((postnumber >= 8900) & (postnumber <= 8961)))

    rin3Cond13 = (((postnumber >= 2301) & (postnumber <= 2308)) | ((postnumber >= 2319) & (postnumber <= 2319)) |
                  ((postnumber >= 2323) & (postnumber <= 2323)) | ((postnumber >= 2325) & (postnumber <= 2329)) |
                  ((postnumber >= 2338) & (postnumber <= 2338)) | ((postnumber >= 2355) & (postnumber <= 2355)) |
                  ((postnumber >= 2365) & (postnumber <= 2365)) | ((postnumber >= 2382) & (postnumber <= 2388)) |
                  ((postnumber >= 2391) & (postnumber <= 2391)) | ((postnumber >= 2600) & (postnumber <= 2609)) |
                  ((postnumber >= 2611) & (postnumber <= 2611)) | ((postnumber >= 2613) & (postnumber <= 2695)) |
                  ((postnumber >= 2801) & (postnumber <= 2985)) | ((postnumber >= 3528) & (postnumber <= 3528)))

    rin3Cond14 = ((postnumber >= 10) & (postnumber <= 1295))

    rin3Cond15 = (((postnumber >= 4001) & (postnumber <= 4395)) | ((postnumber >= 4440) & (postnumber <= 4465)) |
                  ((postnumber >= 5501) & (postnumber <= 5549)) | ((postnumber >= 5560) & (postnumber <= 5589)))

    rin3Cond16 = (((postnumber >= 2500) & (postnumber <= 2584)) | ((postnumber >= 7002) & (postnumber <= 7178)) |
                  ((postnumber >= 7200) & (postnumber <= 7499)) | ((postnumber >= 7540) & (postnumber <= 7549)))

    rin3Cond17 = (((postnumber >= 5716) & (postnumber <= 5718)) | ((postnumber >= 5741) & (postnumber <= 5748)) |
                  ((postnumber >= 5960) & (postnumber <= 5979)) | ((postnumber >= 6700) & (postnumber <= 6996)))

    rin3Cond18 = ((postnumber >= 3650) & (postnumber <= 3999))

    rin3Cond19 = (((postnumber >= 9000) & (postnumber <= 9185)) | ((postnumber >= 9189) & (postnumber <= 9303)) |
                  ((postnumber >= 9305) & (postnumber <= 9389)) | ((postnumber >= 9395) & (postnumber <= 9430)) |
                  ((postnumber >= 9438) & (postnumber <= 9438)) | ((postnumber >= 9465) & (postnumber <= 9465)) |
                  ((postnumber >= 9477) & (postnumber <= 9498)))

    rin3Cond20 = (((postnumber >= 3080) & (postnumber <= 3089)) | ((postnumber >= 3100) & (postnumber <= 3296)))

    rin3Cond21 = (((postnumber >= 4400) & (postnumber <= 4438)) | ((postnumber >= 4473) & (postnumber <= 4720)))

    rin3Cond22 = (((postnumber >= 3539) & (postnumber <= 3540)) | ((postnumber >= 3550) & (postnumber <= 3550)) |
                  ((postnumber >= 3560) & (postnumber <= 3560)) | ((postnumber >= 3570) & (postnumber <= 3570)) |
                  ((postnumber >= 3577) & (postnumber <= 3580)) | ((postnumber >= 3588) & (postnumber <= 3595)))

    conditionList = [rin3Cond1, rin3Cond2, rin3Cond3, rin3Cond4, rin3Cond5, rin3Cond6, rin3Cond7, rin3Cond8,
                     rin3Cond9, rin3Cond10, rin3Cond11, rin3Cond12, rin3Cond13, rin3Cond14, rin3Cond15, rin3Cond16,
                     rin3Cond17, rin3Cond18, rin3Cond19, rin3Cond20, rin3Cond21, rin3Cond22]

    def conditioncheck(conditions):
        rin3 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                rin3 = index + 1
        return rin3

    rin3 = conditioncheck(conditionList)

    return rin3

def rin4(postnumber):
    rin4Cond1 = (((postnumber >= 2440) & (postnumber <= 2448)) | ((postnumber >= 2478) & (postnumber <= 2478)) |
                 ((postnumber >= 2485) & (postnumber <= 2584)) | ((postnumber >= 7002) & (postnumber <= 9991)))

    rin4Cond2 = (((postnumber >= 3001) & (postnumber <= 3490)) | ((postnumber >= 3601) & (postnumber <= 3999)) |
                 ((postnumber >= 4400) & (postnumber <= 4438)) | ((postnumber >= 4473) & (postnumber <= 4994)))

    rin4Cond3 = (((postnumber >= 2668) & (postnumber <= 2669)) | ((postnumber >= 4001) & (postnumber <= 4395)) |
                 ((postnumber >= 4440) & (postnumber <= 4465)) | ((postnumber >= 5003) & (postnumber <= 6996)))

    rin4Cond4 = (((postnumber >= 10) & (postnumber <= 2438)) | ((postnumber >= 2450) & (postnumber <= 2477)) |
                 ((postnumber >= 2480) & (postnumber <= 2482)) | ((postnumber >= 2601) & (postnumber <= 2667)) |
                 ((postnumber >= 2670) & (postnumber <= 2985)) | ((postnumber >= 3501) & (postnumber <= 3595)))

    conditionList = [rin4Cond1, rin4Cond2, rin4Cond3, rin4Cond4]

    def conditioncheck(conditions):
        rin4 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                rin4 = index + 1
        return rin4

    rin4 = conditioncheck(conditionList)

    return rin4

def rin5(postnumber):
    rin5Cond1 = (((postnumber >= 1470) & (postnumber <= 1488)) | ((postnumber >= 1900) & (postnumber <= 1911)) |
                 ((postnumber >= 1920) & (postnumber <= 2093)) | ((postnumber >= 2150) & (postnumber <= 2170)))

    rin5Cond2 = (((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3501) & (postnumber <= 3519)) |
                 ((postnumber >= 3524) & (postnumber <= 3526)) | ((postnumber >= 3529) & (postnumber <= 3538)))

    rin5Cond3 =  ((postnumber >= 4724) & (postnumber <= 4994))

    rin5Cond4 =  (((postnumber >= 3001) & (postnumber <= 3075)) | ((postnumber >= 3090) & (postnumber <= 3095)) |
                  ((postnumber >= 3300) & (postnumber <= 3490)))
    
    rin5Cond5 =  (((postnumber >= 9186) & (postnumber <= 9186)) | ((postnumber >= 9501) & (postnumber <= 9991)))

    rin5Cond6 =  (((postnumber >= 2100) & (postnumber <= 2134)) | ((postnumber >= 2201) & (postnumber <= 2438)) |
                  ((postnumber >= 2450) & (postnumber <= 2477)) | ((postnumber >= 2480) & (postnumber <= 2482)) |
                  ((postnumber >= 2610) & (postnumber <= 2610)) | ((postnumber >= 2612) & (postnumber <= 2612)))

    rin5Cond7 =  (((postnumber >= 5003) & (postnumber <= 5098)) | ((postnumber >= 5107) & (postnumber <= 5111)) |
                  ((postnumber >= 5141) & (postnumber <= 5151)) | ((postnumber >= 5160) & (postnumber <= 5184)) |
                  ((postnumber >= 5237) & (postnumber <= 5237)) | ((postnumber >= 5300) & (postnumber <= 5382)) |
                  ((postnumber >= 5802) & (postnumber <= 5957)) | ((postnumber >= 5981) & (postnumber <= 5994)))

    rin5Cond8 = (((postnumber >= 4198) & (postnumber <= 4299)) | ((postnumber >= 5501) & (postnumber <= 5598)))
    
    rin5Cond9 = (((postnumber >= 5101) & (postnumber <= 5106)) | ((postnumber >= 5113) & (postnumber <= 5137)) |
                 ((postnumber >= 5152) & (postnumber <= 5155)) | ((postnumber >= 5200) & (postnumber <= 5236)) |
                 ((postnumber >= 5238) & (postnumber <= 5299)) | ((postnumber >= 5384) & (postnumber <= 5499)) |
                 ((postnumber >= 5600) & (postnumber <= 5715)) | ((postnumber >= 5719) & (postnumber <= 5736)) |
                 ((postnumber >= 5750) & (postnumber <= 5787)))

    rin5Cond10 = (((postnumber >= 2668) & (postnumber <= 2669)) | ((postnumber >= 6001) & (postnumber <= 6699)))

    rin5Cond11 = (((postnumber >= 7180) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7533)) |
                  ((postnumber >= 7550) & (postnumber <= 7994)) | ((postnumber >= 8601) & (postnumber <= 8985)))

    rin5Cond12 = (((postnumber >= 8000) & (postnumber <= 8591)) | ((postnumber >= 9304) & (postnumber <= 9304)) |
                  ((postnumber >= 9392) & (postnumber <= 9392)) | ((postnumber >= 9436) & (postnumber <= 9476)))

    rin5Cond13 = (((postnumber >= 2601) & (postnumber <= 2609)) | ((postnumber >= 2611) & (postnumber <= 2611)) |
                  ((postnumber >= 2613) & (postnumber <= 2667)) | ((postnumber >= 2670) & (postnumber <= 2985)) |
                  ((postnumber >= 3520) & (postnumber <= 3522)) | ((postnumber >= 3528) & (postnumber <= 3528)) |
                  ((postnumber >= 3539) & (postnumber <= 3595)))

    rin5Cond14 =  (((postnumber >= 10) & (postnumber <= 1295)))

    rin5Cond15 = (((postnumber >= 4001) & (postnumber <= 4187)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                  ((postnumber >= 4440) & (postnumber <= 4465)))
    
    rin5Cond16 =  (((postnumber >= 5718) & (postnumber <= 5718)) | ((postnumber >= 5741) & (postnumber <= 5748)) |
                   ((postnumber >= 5960) & (postnumber <= 5979)) | ((postnumber >= 6700) & (postnumber <= 6996)))

    rin5Cond17 =  (((postnumber >= 2440) & (postnumber <= 2448)) | ((postnumber >= 2478) & (postnumber <= 2478)) |
                   ((postnumber >= 2485) & (postnumber <= 2584)) | ((postnumber >= 7002) & (postnumber <= 7178)) |
                   ((postnumber >= 7200) & (postnumber <= 7496)) | ((postnumber >= 7540) & (postnumber <= 7549)))

    rin5Cond18 = (((postnumber >= 3700) & (postnumber <= 3749)) | ((postnumber >= 3766) & (postnumber <= 3794)) |
                  ((postnumber >= 3900) & (postnumber <= 3999)))

    rin5Cond19 = (((postnumber >= 3601) & (postnumber <= 3697)) | ((postnumber >= 3750) & (postnumber <= 3760)) |
                  ((postnumber >= 3795) & (postnumber <= 3895)))

    rin5Cond20 = (((postnumber >= 9000) & (postnumber <= 9185)) | ((postnumber >= 9189) & (postnumber <= 9303)) |
                  ((postnumber >= 9305) & (postnumber <= 9389)) | ((postnumber >= 9395) & (postnumber <= 9430)) |
                  ((postnumber >= 9479) & (postnumber <= 9498)))

    rin5Cond21 = (((postnumber >= 4400) & (postnumber <= 4438)) | ((postnumber >= 4473) & (postnumber <= 4720)))

    rin5Cond22 = (((postnumber >= 3080) & (postnumber <= 3089)) | ((postnumber >= 3100) & (postnumber <= 3296)))
    
    rin5Cond23 = (((postnumber >= 1600) & (postnumber <= 1798)))

    rin5Cond24 = (((postnumber >= 1400) & (postnumber <= 1458)) | ((postnumber >= 1501) & (postnumber <= 1599)) |
                  ((postnumber >= 1800) & (postnumber <= 1892)) | ((postnumber >= 1912) & (postnumber <= 1914)))

    conditionList = [rin5Cond1, rin5Cond2, rin5Cond3, rin5Cond4, rin5Cond5, rin5Cond6, rin5Cond7, rin5Cond8,
                     rin5Cond9, rin5Cond10, rin5Cond11, rin5Cond12, rin5Cond13, rin5Cond14, rin5Cond15, rin5Cond16, 
                     rin5Cond17, rin5Cond18, rin5Cond19, rin5Cond20, rin5Cond21, rin5Cond22, rin5Cond23, rin5Cond24]

    def conditioncheck(conditions):
        rin5 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                rin5 = index + 1
        return rin5

    rin5 = conditioncheck(conditionList)

    return rin5

def rin6(postnumber):
    rin6Cond1 = (((postnumber >= 4400) & (postnumber <= 4438)) | ((postnumber >= 4473) & (postnumber <= 4994)))

    rin6Cond2 =  (((postnumber >= 1470) & (postnumber <= 1488)) | ((postnumber >= 1900) & (postnumber <= 1911)) |
                  ((postnumber >= 1920) & (postnumber <= 2283)) | ((postnumber >= 2711) & (postnumber <= 2770)) |
                  ((postnumber >= 3520) & (postnumber <= 3522)))

    rin6Cond3 = (((postnumber >= 2301) & (postnumber <= 2438)) | ((postnumber >= 2450) & (postnumber <= 2477)) |
                 ((postnumber >= 2480) & (postnumber <= 2482)) | ((postnumber >= 2601) & (postnumber <= 2667)) |
                 ((postnumber >= 2670) & (postnumber <= 2695)) | ((postnumber >= 2801) & (postnumber <= 2985)) |
                 ((postnumber >= 3528) & (postnumber <= 3528)) | ((postnumber >= 3539) & (postnumber <= 3595)))

    rin6Cond4 = (((postnumber >= 5003) & (postnumber <= 5098)) | ((postnumber >= 5107) & (postnumber <= 5111)) |
                 ((postnumber >= 5141) & (postnumber <= 5151)) | ((postnumber >= 5160) & (postnumber <= 5184)) |
                 ((postnumber >= 5300) & (postnumber <= 5382)) | ((postnumber >= 5802) & (postnumber <= 5957)) |
                 ((postnumber >= 5981) & (postnumber <= 5994)))

    rin6Cond5 = (((postnumber >= 4198) & (postnumber <= 4299)) | ((postnumber >= 5101) & (postnumber <= 5106)) |
                 ((postnumber >= 5113) & (postnumber <= 5137)) | ((postnumber >= 5152) & (postnumber <= 5155)) |
                 ((postnumber >= 5200) & (postnumber <= 5299)) | ((postnumber >= 5384) & (postnumber <= 5715)) |
                 ((postnumber >= 5719) & (postnumber <= 5736)) | ((postnumber >= 5750) & (postnumber <= 5787)))

    rin6Cond6 = (((postnumber >= 2668) & (postnumber <= 2669)) | ((postnumber >= 6001) & (postnumber <= 6699)))

    rin6Cond7 = (((postnumber >= 8000) & (postnumber <= 8591)) | ((postnumber >= 9000) & (postnumber <= 9991)))

    rin6Cond8 = (((postnumber >= 7180) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7533)) |
                 ((postnumber >= 7550) & (postnumber <= 7994)) | ((postnumber >= 8601) & (postnumber <= 8985)))

    rin6Cond9 = (((postnumber >= 180) & (postnumber <= 180)) | ((postnumber >= 182) & (postnumber <= 182)) |
                 ((postnumber >= 185) & (postnumber <= 192)) | ((postnumber >= 195) & (postnumber <= 196)) |
                 ((postnumber >= 465) & (postnumber <= 468)) | ((postnumber >= 475) & (postnumber <= 483)) |
                 ((postnumber >= 486) & (postnumber <= 540)) |  ((postnumber >= 570) & (postnumber <= 694)) |
                 ((postnumber >= 858) & (postnumber <= 1295)))

    rin6Cond10 = (((postnumber >= 10) & (postnumber <= 179)) | ((postnumber >= 181) & (postnumber <= 181)) |
                  ((postnumber >= 183) & (postnumber <= 184)) | ((postnumber >= 193) & (postnumber <= 194)) |
                  ((postnumber >= 198) & (postnumber <= 464)) | ((postnumber >= 469) & (postnumber <= 474)) |
                  ((postnumber >= 484) & (postnumber <= 485)) | ((postnumber >= 550) & (postnumber <= 569)) |
                  ((postnumber >= 701) & (postnumber <= 857)) | ((postnumber >= 1300) & (postnumber <= 1397)) |
                  ((postnumber >= 3501) & (postnumber <= 3519)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                  ((postnumber >= 3529) & (postnumber <= 3538)))

    rin6Cond11 = (((postnumber >= 4001) & (postnumber <= 4187)) | ((postnumber >= 4301) & (postnumber <= 4395)) |
                  ((postnumber >= 4440) & (postnumber <= 4465)))

    rin6Cond12 = (((postnumber >= 5718) & (postnumber <= 5718)) | ((postnumber >= 5741) & (postnumber <= 5748)) |
                  ((postnumber >= 5960) & (postnumber <= 5979)) | ((postnumber >= 6700) & (postnumber <= 6996)))

    rin6Cond13 = (((postnumber >= 2440) & (postnumber <= 2448)) | ((postnumber >= 2478) & (postnumber <= 2478)) |
                  ((postnumber >= 2485) & (postnumber <= 2584)) | ((postnumber >= 7002) & (postnumber <= 7178)) |
                  ((postnumber >= 7200) & (postnumber <= 7496)) | ((postnumber >= 7540) & (postnumber <= 7549)))

    rin6Cond14 = ((postnumber >= 3601) & (postnumber <= 3999))

    rin6Cond15 = ((postnumber >= 3001) & (postnumber <= 3490))

    rin6Cond16 = (((postnumber >= 1400) & (postnumber <= 1458)) | ((postnumber >= 1501) & (postnumber <= 1892)) |
                  ((postnumber >= 1912) & (postnumber <= 1914)))

    conditionList = [rin6Cond1, rin6Cond2, rin6Cond3, rin6Cond4, rin6Cond5, rin6Cond6, rin6Cond7, rin6Cond8,
                     rin6Cond9, rin6Cond10, rin6Cond11, rin6Cond12, rin6Cond13, rin6Cond14, rin6Cond15, rin6Cond16]

    def conditioncheck(conditions):
        rin6 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                rin6 = index + 1
        return rin6

    rin6 = conditioncheck(conditionList)

    return rin6

def swm3(postnumber):
    swm3Cond1 = (((postnumber >= 0) & (postnumber <= 137)) | ((postnumber >= 140) & (postnumber <= 167)) |
                 ((postnumber >= 169) & (postnumber <= 191)) | ((postnumber >= 199) & (postnumber <= 261)) |
                 ((postnumber >= 268) & (postnumber <= 268)) | ((postnumber >= 272) & (postnumber <= 274)) |
                 ((postnumber >= 279) & (postnumber <= 280)) | ((postnumber >= 288) & (postnumber <= 312)) |
                 ((postnumber >= 314) & (postnumber <= 323)) | ((postnumber >= 341) & (postnumber <= 349)) |
                 ((postnumber >= 351) & (postnumber <= 351)) | ((postnumber >= 353) & (postnumber <= 353)) |
                 ((postnumber >= 355) & (postnumber <= 357)) | ((postnumber >= 359) & (postnumber <= 369)) |
                 ((postnumber >= 384) & (postnumber <= 444)) | ((postnumber >= 480) & (postnumber <= 480)) |
                 ((postnumber >= 497) & (postnumber <= 540)) | ((postnumber >= 559) & (postnumber <= 559)) |
                 ((postnumber >= 564) & (postnumber <= 564)) | ((postnumber >= 592) & (postnumber <= 592)) |
                 ((postnumber >= 595) & (postnumber <= 595)) | ((postnumber >= 599) & (postnumber <= 645)) |
                 ((postnumber >= 669) & (postnumber <= 670)) | ((postnumber >= 672) & (postnumber <= 672)) |
                 ((postnumber >= 674) & (postnumber <= 674)) | ((postnumber >= 677) & (postnumber <= 677)) |
                 ((postnumber >= 684) & (postnumber <= 684)) | ((postnumber >= 690) & (postnumber <= 690)) |
                 ((postnumber >= 695) & (postnumber <= 750)) | ((postnumber >= 752) & (postnumber <= 752)) |
                 ((postnumber >= 757) & (postnumber <= 757)) | ((postnumber >= 759) & (postnumber <= 765)) |
                 ((postnumber >= 769) & (postnumber <= 770)) | ((postnumber >= 772) & (postnumber <= 772)) |
                 ((postnumber >= 774) & (postnumber <= 775)) | ((postnumber >= 778) & (postnumber <= 783)) |
                 ((postnumber >= 785) & (postnumber <= 785)) | ((postnumber >= 788) & (postnumber <= 789)) |
                 ((postnumber >= 792) & (postnumber <= 840)) | ((postnumber >= 854) & (postnumber <= 854)) |
                 ((postnumber >= 856) & (postnumber <= 857)) | ((postnumber >= 871) & (postnumber <= 871)) |
                 ((postnumber >= 873) & (postnumber <= 874)) | ((postnumber >= 877) & (postnumber <= 877)) |
                 ((postnumber >= 882) & (postnumber <= 883)) | ((postnumber >= 892) & (postnumber <= 915)) |
                 ((postnumber >= 957) & (postnumber <= 957)) | ((postnumber >= 964) & (postnumber <= 968)) |
                 ((postnumber >= 972) & (postnumber <= 972)) | ((postnumber >= 983) & (postnumber <= 983)) |
                 ((postnumber >= 987) & (postnumber <= 987)) | ((postnumber >= 989) & (postnumber <= 1011)) |
                 ((postnumber >= 1052) & (postnumber <= 1053)) | ((postnumber >= 1055) & (postnumber <= 1056)) |
                 ((postnumber >= 1062) & (postnumber <= 1062)) | ((postnumber >= 1070) & (postnumber <= 1071)) |
                 ((postnumber >= 1084) & (postnumber <= 1084)) | ((postnumber >= 1087) & (postnumber <= 1087)) |
                 ((postnumber >= 1089) & (postnumber <= 1112)) | ((postnumber >= 1151) & (postnumber <= 1151)) |
                 ((postnumber >= 1156) & (postnumber <= 1156)) | ((postnumber >= 1158) & (postnumber <= 1158)) |
                 ((postnumber >= 1161) & (postnumber <= 1161)) | ((postnumber >= 1166) & (postnumber <= 1168)) |
                 ((postnumber >= 1170) & (postnumber <= 1172)) | ((postnumber >= 1179) & (postnumber <= 1179)) |
                 ((postnumber >= 1185) & (postnumber <= 1185)) | ((postnumber >= 1189) & (postnumber <= 1215)) |
                 ((postnumber >= 1253) & (postnumber <= 1253)) | ((postnumber >= 1257) & (postnumber <= 1257)) |
                 ((postnumber >= 1260) & (postnumber <= 1262)) | ((postnumber >= 1267) & (postnumber <= 1274)) |
                 ((postnumber >= 1276) & (postnumber <= 1277)) | ((postnumber >= 1282) & (postnumber <= 1284)) |
                 ((postnumber >= 1286) & (postnumber <= 1294)))

    swm3Cond2 = (((postnumber >= 138) & (postnumber <= 139)) | ((postnumber >= 192) & (postnumber <= 198)) |
                 ((postnumber >= 656) & (postnumber <= 661)) | ((postnumber >= 663) & (postnumber <= 667)) |
                 ((postnumber >= 671) & (postnumber <= 671)) | ((postnumber >= 673) & (postnumber <= 673)) |
                 ((postnumber >= 675) & (postnumber <= 676)) | ((postnumber >= 678) & (postnumber <= 681)) |
                 ((postnumber >= 688) & (postnumber <= 688)) | ((postnumber >= 1113) & (postnumber <= 1150)) |
                 ((postnumber >= 1152) & (postnumber <= 1155)) | ((postnumber >= 1157) & (postnumber <= 1157)) |
                 ((postnumber >= 1159) & (postnumber <= 1160)) | ((postnumber >= 1162) & (postnumber <= 1165)) |
                 ((postnumber >= 1169) & (postnumber <= 1169)) | ((postnumber >= 1173) & (postnumber <= 1178)) |
                 ((postnumber >= 1180) & (postnumber <= 1184)) | ((postnumber >= 1186) & (postnumber <= 1188)) |
                 ((postnumber >= 1216) & (postnumber <= 1252)) | ((postnumber >= 1254) & (postnumber <= 1256)) |
                 ((postnumber >= 1258) & (postnumber <= 1259)) | ((postnumber >= 1263) & (postnumber <= 1266)) |
                 ((postnumber >= 1275) & (postnumber <= 1275)) | ((postnumber >= 1278) & (postnumber <= 1281)) |
                 ((postnumber >= 1285) & (postnumber <= 1285)) | ((postnumber >= 1295) & (postnumber <= 1295)) |
                 ((postnumber >= 1398) & (postnumber <= 1459)) | ((postnumber >= 1471) & (postnumber <= 1471)) |
                 ((postnumber >= 1483) & (postnumber <= 1483)) | ((postnumber >= 3473) & (postnumber <= 3475)) |
                 ((postnumber >= 3477) & (postnumber <= 3477)) | ((postnumber >= 3479) & (postnumber <= 3480)) |
                 ((postnumber >= 3482) & (postnumber <= 3490)))

    swm3Cond3 = (((postnumber >= 168) & (postnumber <= 168)) | ((postnumber >= 262) & (postnumber <= 267)) |
                 ((postnumber >= 269) & (postnumber <= 271)) | ((postnumber >= 313) & (postnumber <= 313)) |
                 ((postnumber >= 324) & (postnumber <= 340)) | ((postnumber >= 350) & (postnumber <= 350)) |
                 ((postnumber >= 352) & (postnumber <= 352)) | ((postnumber >= 354) & (postnumber <= 354)) |
                 ((postnumber >= 358) & (postnumber <= 358)) | ((postnumber >= 370) & (postnumber <= 375)) |
                 ((postnumber >= 446) & (postnumber <= 456)) | ((postnumber >= 484) & (postnumber <= 484)) |
                 ((postnumber >= 541) & (postnumber <= 550)) | ((postnumber >= 581) & (postnumber <= 582)) |
                 ((postnumber >= 682) & (postnumber <= 683)) | ((postnumber >= 685) & (postnumber <= 687)) |
                 ((postnumber >= 689) & (postnumber <= 689)) | ((postnumber >= 691) & (postnumber <= 694)) |
                 ((postnumber >= 751) & (postnumber <= 751)) | ((postnumber >= 753) & (postnumber <= 754)) |
                 ((postnumber >= 756) & (postnumber <= 756)) | ((postnumber >= 758) & (postnumber <= 758)) |
                 ((postnumber >= 766) & (postnumber <= 766)) | ((postnumber >= 768) & (postnumber <= 768)) |
                 ((postnumber >= 771) & (postnumber <= 771)) | ((postnumber >= 773) & (postnumber <= 773)) |
                 ((postnumber >= 776) & (postnumber <= 776)) | ((postnumber >= 784) & (postnumber <= 784)) |
                 ((postnumber >= 851) & (postnumber <= 851)) | ((postnumber >= 916) & (postnumber <= 951)) |
                 ((postnumber >= 953) & (postnumber <= 956)) | ((postnumber >= 958) & (postnumber <= 963)) |
                 ((postnumber >= 969) & (postnumber <= 971)) | ((postnumber >= 973) & (postnumber <= 973)))

    swm3Cond4 = (((postnumber >= 275) & (postnumber <= 278)) | ((postnumber >= 281) & (postnumber <= 287)) |
                 ((postnumber >= 376) & (postnumber <= 383)) | ((postnumber >= 755) & (postnumber <= 755)) |
                 ((postnumber >= 767) & (postnumber <= 767)) | ((postnumber >= 777) & (postnumber <= 777)) |
                 ((postnumber >= 1296) & (postnumber <= 1397)) | ((postnumber >= 3402) & (postnumber <= 3410)) |
                 ((postnumber >= 3413) & (postnumber <= 3420)) | ((postnumber >= 3427) & (postnumber <= 3430)) |
                 ((postnumber >= 3432) & (postnumber <= 3440)) | ((postnumber >= 3442) & (postnumber <= 3470)) |
                 ((postnumber >= 3472) & (postnumber <= 3472)) | ((postnumber >= 3478) & (postnumber <= 3478)))

    swm3Cond5 = (((postnumber >= 445) & (postnumber <= 445)) | ((postnumber >= 457) & (postnumber <= 479)) |
                 ((postnumber >= 481) & (postnumber <= 483)) | ((postnumber >= 485) & (postnumber <= 496)) |
                 ((postnumber >= 551) & (postnumber <= 558)) | ((postnumber >= 560) & (postnumber <= 563)) |
                 ((postnumber >= 565) & (postnumber <= 580)) | ((postnumber >= 583) & (postnumber <= 591)) |
                 ((postnumber >= 593) & (postnumber <= 594)) | ((postnumber >= 596) & (postnumber <= 598)) |
                 ((postnumber >= 646) & (postnumber <= 655)) | ((postnumber >= 662) & (postnumber <= 662)) |
                 ((postnumber >= 668) & (postnumber <= 668)) | ((postnumber >= 786) & (postnumber <= 787)) |
                 ((postnumber >= 790) & (postnumber <= 791)) | ((postnumber >= 841) & (postnumber <= 850)) |
                 ((postnumber >= 852) & (postnumber <= 853)) | ((postnumber >= 855) & (postnumber <= 855)) |
                 ((postnumber >= 858) & (postnumber <= 870)) | ((postnumber >= 872) & (postnumber <= 872)) |
                 ((postnumber >= 875) & (postnumber <= 876)) | ((postnumber >= 878) & (postnumber <= 881)) |
                 ((postnumber >= 884) & (postnumber <= 891)) | ((postnumber >= 952) & (postnumber <= 952)) |
                 ((postnumber >= 974) & (postnumber <= 982)) | ((postnumber >= 984) & (postnumber <= 986)) |
                 ((postnumber >= 988) & (postnumber <= 988)) | ((postnumber >= 1012) & (postnumber <= 1051)) |
                 ((postnumber >= 1054) & (postnumber <= 1054)) | ((postnumber >= 1057) & (postnumber <= 1061)) |
                 ((postnumber >= 1063) & (postnumber <= 1069)) | ((postnumber >= 1072) & (postnumber <= 1083)) |
                 ((postnumber >= 1085) & (postnumber <= 1086)) | ((postnumber >= 1088) & (postnumber <= 1088)))

    swm3Cond6 = (((postnumber >= 1460) & (postnumber <= 1470)) | ((postnumber >= 1472) & (postnumber <= 1482)) |
                 ((postnumber >= 1484) & (postnumber <= 1488)) | ((postnumber >= 1807) & (postnumber <= 1811)) |
                 ((postnumber >= 1813) & (postnumber <= 1815)) | ((postnumber >= 1828) & (postnumber <= 1850)) |
                 ((postnumber >= 1852) & (postnumber <= 1860)) | ((postnumber >= 1862) & (postnumber <= 1870)) |
                 ((postnumber >= 1872) & (postnumber <= 1880)) | ((postnumber >= 1891) & (postnumber <= 2027)) |
                 ((postnumber >= 2031) & (postnumber <= 2031)) | ((postnumber >= 2035) & (postnumber <= 2053)) |
                 ((postnumber >= 2066) & (postnumber <= 2069)) | ((postnumber >= 2135) & (postnumber <= 2150)) |
                 ((postnumber >= 2152) & (postnumber <= 2170)))

    swm3Cond7 = (((postnumber >= 1489) & (postnumber <= 1806)) | ((postnumber >= 1812) & (postnumber <= 1812)) |
                 ((postnumber >= 1816) & (postnumber <= 1827)) | ((postnumber >= 1851) & (postnumber <= 1851)) |
                 ((postnumber >= 1861) & (postnumber <= 1861)) | ((postnumber >= 1871) & (postnumber <= 1871)) |
                 ((postnumber >= 1881) & (postnumber <= 1890)))

    swm3Cond8 = (((postnumber >= 2028) & (postnumber <= 2030)) | ((postnumber >= 2032) & (postnumber <= 2034)) |
                 ((postnumber >= 2054) & (postnumber <= 2065)) | ((postnumber >= 2070) & (postnumber <= 2134)) |
                 ((postnumber >= 2151) & (postnumber <= 2151)) | ((postnumber >= 2171) & (postnumber <= 2319)) |
                 ((postnumber >= 2321) & (postnumber <= 2345)) | ((postnumber >= 2406) & (postnumber <= 2415)) |
                 ((postnumber >= 2420) & (postnumber <= 2420)) | ((postnumber >= 2422) & (postnumber <= 2428)) |
                 ((postnumber >= 2430) & (postnumber <= 2436)) | ((postnumber >= 2438) & (postnumber <= 2450)) |
                 ((postnumber >= 2452) & (postnumber <= 2480)) | ((postnumber >= 2609) & (postnumber <= 2609)) |
                 ((postnumber >= 2611) & (postnumber <= 2611)) | ((postnumber >= 2613) & (postnumber <= 2613)) |
                 ((postnumber >= 2615) & (postnumber <= 2615)) | ((postnumber >= 2618) & (postnumber <= 2619)) |
                 ((postnumber >= 2622) & (postnumber <= 2624)))

    swm3Cond9 = (((postnumber >= 2320) & (postnumber <= 2320)) | ((postnumber >= 2346) & (postnumber <= 2405)) |
                 ((postnumber >= 2416) & (postnumber <= 2419)) | ((postnumber >= 2421) & (postnumber <= 2421)) |
                 ((postnumber >= 2429) & (postnumber <= 2429)) | ((postnumber >= 2437) & (postnumber <= 2437)) |
                 ((postnumber >= 2451) & (postnumber <= 2451)) | ((postnumber >= 2481) & (postnumber <= 2482)) |
                 ((postnumber >= 2486) & (postnumber <= 2487)) | ((postnumber >= 2501) & (postnumber <= 2501)) |
                 ((postnumber >= 2543) & (postnumber <= 2544)) | ((postnumber >= 2585) & (postnumber <= 2608)) |
                 ((postnumber >= 2610) & (postnumber <= 2610)) | ((postnumber >= 2612) & (postnumber <= 2612)) |
                 ((postnumber >= 2614) & (postnumber <= 2614)) | ((postnumber >= 2616) & (postnumber <= 2617)) |
                 ((postnumber >= 2620) & (postnumber <= 2621)) | ((postnumber >= 2625) & (postnumber <= 2663)) |
                 ((postnumber >= 2670) & (postnumber <= 2694)) | ((postnumber >= 2696) & (postnumber <= 2985)) |
                 ((postnumber >= 3520) & (postnumber <= 3520)) | ((postnumber >= 3522) & (postnumber <= 3522)) |
                 ((postnumber >= 3527) & (postnumber <= 3528)))

    swm3Cond10 = (((postnumber >= 2483) & (postnumber <= 2485)) | ((postnumber >= 2488) & (postnumber <= 2500)) |
                  ((postnumber >= 2502) & (postnumber <= 2542)) | ((postnumber >= 2545) & (postnumber <= 2584)) |
                  ((postnumber >= 6690) & (postnumber <= 6690)) | ((postnumber >= 6694) & (postnumber <= 6697)) |
                  ((postnumber >= 6699) & (postnumber <= 6699)) | ((postnumber >= 6997) & (postnumber <= 7003)) |
                  ((postnumber >= 7005) & (postnumber <= 7005)) | ((postnumber >= 7007) & (postnumber <= 7009)) |
                  ((postnumber >= 7014) & (postnumber <= 7015)) | ((postnumber >= 7019) & (postnumber <= 7019)) |
                  ((postnumber >= 7028) & (postnumber <= 7028)) | ((postnumber >= 7030) & (postnumber <= 7030)) |
                  ((postnumber >= 7032) & (postnumber <= 7033)) | ((postnumber >= 7035) & (postnumber <= 7046)) |
                  ((postnumber >= 7048) & (postnumber <= 7070)) | ((postnumber >= 7073) & (postnumber <= 7074)) |
                  ((postnumber >= 7083) & (postnumber <= 7084)) | ((postnumber >= 7195) & (postnumber <= 7338)) |
                  ((postnumber >= 7346) & (postnumber <= 7499)))

    swm3Cond11 = (((postnumber >= 2664) & (postnumber <= 2669)) | ((postnumber >= 6093) & (postnumber <= 6094)) |
                  ((postnumber >= 6215) & (postnumber <= 6215)) | ((postnumber >= 6240) & (postnumber <= 6240)) |
                  ((postnumber >= 6250) & (postnumber <= 6250)) | ((postnumber >= 6260) & (postnumber <= 6260)) |
                  ((postnumber >= 6264) & (postnumber <= 6280)) | ((postnumber >= 6286) & (postnumber <= 6300)) |
                  ((postnumber >= 6310) & (postnumber <= 6330)) | ((postnumber >= 6340) & (postnumber <= 6394)) |
                  ((postnumber >= 6399) & (postnumber <= 6689)) | ((postnumber >= 6691) & (postnumber <= 6693)) |
                  ((postnumber >= 6698) & (postnumber <= 6698)) | ((postnumber >= 7339) & (postnumber <= 7345)))

    swm3Cond12 = (((postnumber >= 2695) & (postnumber <= 2695)) | ((postnumber >= 5995) & (postnumber <= 6092)) |
                  ((postnumber >= 6095) & (postnumber <= 6214)) | ((postnumber >= 6216) & (postnumber <= 6239)) |
                  ((postnumber >= 6241) & (postnumber <= 6249)) | ((postnumber >= 6251) & (postnumber <= 6259)) |
                  ((postnumber >= 6261) & (postnumber <= 6263)) | ((postnumber >= 6281) & (postnumber <= 6285)) |
                  ((postnumber >= 6301) & (postnumber <= 6309)) | ((postnumber >= 6331) & (postnumber <= 6339)) |
                  ((postnumber >= 6395) & (postnumber <= 6398)) | ((postnumber >= 6700) & (postnumber <= 6799)) |
                  ((postnumber >= 6818) & (postnumber <= 6819)) | ((postnumber >= 6822) & (postnumber <= 6823)) |
                  ((postnumber >= 6826) & (postnumber <= 6827)) | ((postnumber >= 6829) & (postnumber <= 6829)) |
                  ((postnumber >= 6858) & (postnumber <= 6858)) | ((postnumber >= 6913) & (postnumber <= 6915)) |
                  ((postnumber >= 6917) & (postnumber <= 6917)) | ((postnumber >= 6919) & (postnumber <= 6919)) |
                  ((postnumber >= 6927) & (postnumber <= 6927)) | ((postnumber >= 6984) & (postnumber <= 6984)))

    swm3Cond13 = (((postnumber >= 2986) & (postnumber <= 3007)) | ((postnumber >= 3009) & (postnumber <= 3012)) |
                  ((postnumber >= 3014) & (postnumber <= 3021)) | ((postnumber >= 3023) & (postnumber <= 3026)) |
                  ((postnumber >= 3028) & (postnumber <= 3030)) | ((postnumber >= 3032) & (postnumber <= 3034)) |
                  ((postnumber >= 3036) & (postnumber <= 3038)) | ((postnumber >= 3040) & (postnumber <= 3045)) |
                  ((postnumber >= 3048) & (postnumber <= 3048)) | ((postnumber >= 3051) & (postnumber <= 3054)) |
                  ((postnumber >= 3056) & (postnumber <= 3056)) | ((postnumber >= 3058) & (postnumber <= 3100)) |
                  ((postnumber >= 3172) & (postnumber <= 3172)) | ((postnumber >= 3175) & (postnumber <= 3177)) |
                  ((postnumber >= 3179) & (postnumber <= 3199)) | ((postnumber >= 3243) & (postnumber <= 3243)) |
                  ((postnumber >= 3275) & (postnumber <= 3275)) | ((postnumber >= 3277) & (postnumber <= 3277)) |
                  ((postnumber >= 3281) & (postnumber <= 3282)) | ((postnumber >= 3323) & (postnumber <= 3330)) |
                  ((postnumber >= 3577) & (postnumber <= 3577)) | ((postnumber >= 3582) & (postnumber <= 3588)) |
                  ((postnumber >= 3594) & (postnumber <= 3595)) | ((postnumber >= 3600) & (postnumber <= 3612)) |
                  ((postnumber >= 3614) & (postnumber <= 3621)) | ((postnumber >= 3623) & (postnumber <= 3760)) |
                  ((postnumber >= 3771) & (postnumber <= 3784)) | ((postnumber >= 3791) & (postnumber <= 3900)) |
                  ((postnumber >= 3910) & (postnumber <= 3911)) | ((postnumber >= 3913) & (postnumber <= 3913)) |
                  ((postnumber >= 3961) & (postnumber <= 3965)) | ((postnumber >= 4735) & (postnumber <= 4737)) |
                  ((postnumber >= 4742) & (postnumber <= 4742)) | ((postnumber >= 4746) & (postnumber <= 4747)) |
                  ((postnumber >= 4755) & (postnumber <= 4755)) | ((postnumber >= 4865) & (postnumber <= 4865)))

    swm3Cond14 = (((postnumber >= 3008) & (postnumber <= 3008)) | ((postnumber >= 3013) & (postnumber <= 3013)) |
                  ((postnumber >= 3022) & (postnumber <= 3022)) | ((postnumber >= 3027) & (postnumber <= 3027)) |
                  ((postnumber >= 3031) & (postnumber <= 3031)) | ((postnumber >= 3035) & (postnumber <= 3035)) |
                  ((postnumber >= 3039) & (postnumber <= 3039)) | ((postnumber >= 3046) & (postnumber <= 3047)) |
                  ((postnumber >= 3049) & (postnumber <= 3050)) | ((postnumber >= 3055) & (postnumber <= 3055)) |
                  ((postnumber >= 3057) & (postnumber <= 3057)) | ((postnumber >= 3297) & (postnumber <= 3322)) |
                  ((postnumber >= 3331) & (postnumber <= 3401)) | ((postnumber >= 3411) & (postnumber <= 3412)) |
                  ((postnumber >= 3421) & (postnumber <= 3426)) | ((postnumber >= 3431) & (postnumber <= 3431)) |
                  ((postnumber >= 3441) & (postnumber <= 3441)) | ((postnumber >= 3471) & (postnumber <= 3471)) |
                  ((postnumber >= 3476) & (postnumber <= 3476)) | ((postnumber >= 3481) & (postnumber <= 3481)) |
                  ((postnumber >= 3491) & (postnumber <= 3519)) | ((postnumber >= 3521) & (postnumber <= 3521)) |
                  ((postnumber >= 3523) & (postnumber <= 3526)) | ((postnumber >= 3529) & (postnumber <= 3576)) |
                  ((postnumber >= 3578) & (postnumber <= 3581)) | ((postnumber >= 3589) & (postnumber <= 3593)) |
                  ((postnumber >= 3596) & (postnumber <= 3599)) | ((postnumber >= 3613) & (postnumber <= 3613)) |
                  ((postnumber >= 3622) & (postnumber <= 3622)))

    swm3Cond15 = (((postnumber >= 3101) & (postnumber <= 3171)) | ((postnumber >= 3173) & (postnumber <= 3174)) |
                  ((postnumber >= 3178) & (postnumber <= 3178)) | ((postnumber >= 3200) & (postnumber <= 3242)) |
                  ((postnumber >= 3244) & (postnumber <= 3274)) | ((postnumber >= 3276) & (postnumber <= 3276)) |
                  ((postnumber >= 3278) & (postnumber <= 3280)) | ((postnumber >= 3283) & (postnumber <= 3296)) |
                  ((postnumber >= 3761) & (postnumber <= 3770)) | ((postnumber >= 3785) & (postnumber <= 3790)) |
                  ((postnumber >= 3901) & (postnumber <= 3909)) | ((postnumber >= 3912) & (postnumber <= 3912)) |
                  ((postnumber >= 3914) & (postnumber <= 3960)) | ((postnumber >= 3966) & (postnumber <= 3999)) |
                  ((postnumber >= 4635) & (postnumber <= 4639)) | ((postnumber >= 4648) & (postnumber <= 4657)) |
                  ((postnumber >= 4703) & (postnumber <= 4705)) | ((postnumber >= 4721) & (postnumber <= 4734)) |
                  ((postnumber >= 4738) & (postnumber <= 4741)) | ((postnumber >= 4743) & (postnumber <= 4745)) |
                  ((postnumber >= 4748) & (postnumber <= 4754)) | ((postnumber >= 4756) & (postnumber <= 4864)) |
                  ((postnumber >= 4866) & (postnumber <= 4994)))

    swm3Cond16 = (((postnumber >= 4000) & (postnumber <= 4053)) | ((postnumber >= 4055) & (postnumber <= 4150)) |
                  ((postnumber >= 4153) & (postnumber <= 4157)) | ((postnumber >= 4161) & (postnumber <= 4198)))

    swm3Cond17 = (((postnumber >= 4054) & (postnumber <= 4054)) | ((postnumber >= 4159) & (postnumber <= 4160)) |
                  ((postnumber >= 4300) & (postnumber <= 4634)) | ((postnumber >= 4640) & (postnumber <= 4647)) |
                  ((postnumber >= 4658) & (postnumber <= 4702)) | ((postnumber >= 4706) & (postnumber <= 4720)))

    swm3Cond18 = (((postnumber >= 4151) & (postnumber <= 4152)) | ((postnumber >= 4158) & (postnumber <= 4158)) |
                  ((postnumber >= 4199) & (postnumber <= 4299)) | ((postnumber >= 5185) & (postnumber <= 5204)) |
                  ((postnumber >= 5208) & (postnumber <= 5217)) | ((postnumber >= 5400) & (postnumber <= 5598)) |
                  ((postnumber >= 5601) & (postnumber <= 5605)) | ((postnumber >= 5621) & (postnumber <= 5629)) |
                  ((postnumber >= 5633) & (postnumber <= 5649)) | ((postnumber >= 5653) & (postnumber <= 5696)) |
                  ((postnumber >= 5749) & (postnumber <= 5750)) | ((postnumber >= 5752) & (postnumber <= 5778)) |
                  ((postnumber >= 5780) & (postnumber <= 5781)) | ((postnumber >= 5783) & (postnumber <= 5785)))

    swm3Cond19 = (((postnumber >= 4995) & (postnumber <= 5037)) | ((postnumber >= 5040) & (postnumber <= 5041)) |
                  ((postnumber >= 5043) & (postnumber <= 5043)) | ((postnumber >= 5046) & (postnumber <= 5068)) |
                  ((postnumber >= 5072) & (postnumber <= 5073)) | ((postnumber >= 5076) & (postnumber <= 5097)) |
                  ((postnumber >= 5099) & (postnumber <= 5099)) | ((postnumber >= 5152) & (postnumber <= 5155)) |
                  ((postnumber >= 5220) & (postnumber <= 5244)) | ((postnumber >= 5249) & (postnumber <= 5286)) |
                  ((postnumber >= 5383) & (postnumber <= 5392)) | ((postnumber >= 5394) & (postnumber <= 5398)) |
                  ((postnumber >= 6801) & (postnumber <= 6807)) | ((postnumber >= 6820) & (postnumber <= 6821)) |
                  ((postnumber >= 6824) & (postnumber <= 6825)) | ((postnumber >= 6828) & (postnumber <= 6828)) |
                  ((postnumber >= 6830) & (postnumber <= 6841)) | ((postnumber >= 6901) & (postnumber <= 6907)) |
                  ((postnumber >= 6989) & (postnumber <= 6991)))

    swm3Cond20 = (((postnumber >= 5038) & (postnumber <= 5039)) | ((postnumber >= 5042) & (postnumber <= 5042)) |
                  ((postnumber >= 5044) & (postnumber <= 5045)) | ((postnumber >= 5069) & (postnumber <= 5071)) |
                  ((postnumber >= 5074) & (postnumber <= 5075)) | ((postnumber >= 5098) & (postnumber <= 5098)) |
                  ((postnumber >= 5100) & (postnumber <= 5151)) | ((postnumber >= 5156) & (postnumber <= 5184)) |
                  ((postnumber >= 5205) & (postnumber <= 5207)) | ((postnumber >= 5218) & (postnumber <= 5219)) |
                  ((postnumber >= 5245) & (postnumber <= 5248)) | ((postnumber >= 5287) & (postnumber <= 5382)) |
                  ((postnumber >= 5393) & (postnumber <= 5393)) | ((postnumber >= 5399) & (postnumber <= 5399)) |
                  ((postnumber >= 5599) & (postnumber <= 5600)) | ((postnumber >= 5606) & (postnumber <= 5620)) |
                  ((postnumber >= 5630) & (postnumber <= 5632)) | ((postnumber >= 5650) & (postnumber <= 5652)) |
                  ((postnumber >= 5697) & (postnumber <= 5748)) | ((postnumber >= 5751) & (postnumber <= 5751)) |
                  ((postnumber >= 5779) & (postnumber <= 5779)) | ((postnumber >= 5782) & (postnumber <= 5782)) |
                  ((postnumber >= 5786) & (postnumber <= 5994)) | ((postnumber >= 6800) & (postnumber <= 6800)) |
                  ((postnumber >= 6808) & (postnumber <= 6817)) | ((postnumber >= 6842) & (postnumber <= 6857)) |
                  ((postnumber >= 6859) & (postnumber <= 6900)) | ((postnumber >= 6908) & (postnumber <= 6912)) |
                  ((postnumber >= 6916) & (postnumber <= 6916)) | ((postnumber >= 6918) & (postnumber <= 6918)) |
                  ((postnumber >= 6920) & (postnumber <= 6926)) | ((postnumber >= 6928) & (postnumber <= 6983)) |
                  ((postnumber >= 6985) & (postnumber <= 6988)) | ((postnumber >= 6992) & (postnumber <= 6996)))

    swm3Cond21 = (((postnumber >= 7004) & (postnumber <= 7004)) | ((postnumber >= 7006) & (postnumber <= 7006)) |
                  ((postnumber >= 7010) & (postnumber <= 7013)) | ((postnumber >= 7016) & (postnumber <= 7018)) |
                  ((postnumber >= 7020) & (postnumber <= 7027)) | ((postnumber >= 7029) & (postnumber <= 7029)) |
                  ((postnumber >= 7031) & (postnumber <= 7031)) | ((postnumber >= 7034) & (postnumber <= 7034)) |
                  ((postnumber >= 7047) & (postnumber <= 7047)) | ((postnumber >= 7071) & (postnumber <= 7072)) |
                  ((postnumber >= 7075) & (postnumber <= 7082)) | ((postnumber >= 7085) & (postnumber <= 7099)) |
                  ((postnumber >= 7502) & (postnumber <= 7502)) | ((postnumber >= 7507) & (postnumber <= 7507)) |
                  ((postnumber >= 7513) & (postnumber <= 7513)) | ((postnumber >= 7515) & (postnumber <= 7517)) |
                  ((postnumber >= 7534) & (postnumber <= 7570)))

    swm3Cond22 = (((postnumber >= 7100) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7501)) |
                  ((postnumber >= 7503) & (postnumber <= 7506)) | ((postnumber >= 7508) & (postnumber <= 7512)) |
                  ((postnumber >= 7514) & (postnumber <= 7514)) | ((postnumber >= 7518) & (postnumber <= 7533)) |
                  ((postnumber >= 7571) & (postnumber <= 7977)) | ((postnumber >= 7981) & (postnumber <= 7994)))

    swm3Cond23 = (((postnumber >= 7978) & (postnumber <= 7980)) | ((postnumber >= 7995) & (postnumber <= 8058)) |
                  ((postnumber >= 8065) & (postnumber <= 8298)) | ((postnumber >= 8592) & (postnumber <= 8985)) |
                  ((postnumber >= 9441) & (postnumber <= 9441)) | ((postnumber >= 9444) & (postnumber <= 9444)))

    swm3Cond24 = (((postnumber >= 8059) & (postnumber <= 8064)) | ((postnumber >= 8299) & (postnumber <= 8591)) |
                  ((postnumber >= 9198) & (postnumber <= 9200)) | ((postnumber >= 9300) & (postnumber <= 9440)) |
                  ((postnumber >= 9442) & (postnumber <= 9443)) | ((postnumber >= 9451) & (postnumber <= 9453)) |
                  ((postnumber >= 9456) & (postnumber <= 9465)) | ((postnumber >= 9471) & (postnumber <= 9498)))

    swm3Cond25 = (((postnumber >= 8986) & (postnumber <= 9197)) | ((postnumber >= 9201) & (postnumber <= 9299)) |
                  ((postnumber >= 9445) & (postnumber <= 9450)) | ((postnumber >= 9454) & (postnumber <= 9455)) |
                  ((postnumber >= 9466) & (postnumber <= 9470)) | ((postnumber >= 9499) & (postnumber <= 9991)))

    conditionList = [swm3Cond1, swm3Cond2, swm3Cond3, swm3Cond4, swm3Cond5, swm3Cond6, swm3Cond7, swm3Cond8,
                     swm3Cond9, swm3Cond10, swm3Cond11, swm3Cond12, swm3Cond13, swm3Cond14, swm3Cond15, swm3Cond16,
                     swm3Cond17, swm3Cond18, swm3Cond19, swm3Cond20, swm3Cond21, swm3Cond22, swm3Cond23, swm3Cond24,
                     swm3Cond25]

    def conditioncheck(conditions):
        swm3 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                swm3 = index + 1
        return swm3

    swm3 = conditioncheck(conditionList)

    return swm3

def swm4(postnumber):
    swm4Cond1 = (((postnumber >= 2030) & (postnumber <= 2034)) | ((postnumber >= 2055) & (postnumber <= 2066)) |
                 ((postnumber >= 2070) & (postnumber <= 2134)) | ((postnumber >= 2200) & (postnumber <= 2319)) |
                 ((postnumber >= 2321) & (postnumber <= 2345)) | ((postnumber >= 2401) & (postnumber <= 2482)) |
                 ((postnumber >= 2544) & (postnumber <= 2544)) | ((postnumber >= 2609) & (postnumber <= 2609)) |
                 ((postnumber >= 2611) & (postnumber <= 2611)) | ((postnumber >= 2613) & (postnumber <= 2615)) |
                 ((postnumber >= 2618) & (postnumber <= 2624)) | ((postnumber >= 2626) & (postnumber <= 2629)))

    swm4Cond2 = (((postnumber >= 9060) & (postnumber <= 9060)) | ((postnumber >= 9069) & (postnumber <= 9080)) |
                 ((postnumber >= 9110) & (postnumber <= 9152)) | ((postnumber >= 9156) & (postnumber <= 9197)) |
                 ((postnumber >= 9445) & (postnumber <= 9446)) | ((postnumber >= 9453) & (postnumber <= 9470)) |
                 ((postnumber >= 9501) & (postnumber <= 9991)))

    swm4Cond3 = (((postnumber >= 4001) & (postnumber <= 4053)) | ((postnumber >= 4055) & (postnumber <= 4150)) |
                 ((postnumber >= 4156) & (postnumber <= 4156)) | ((postnumber >= 4163) & (postnumber <= 4198)) |
                 ((postnumber >= 4313) & (postnumber <= 4313)))

    swm4Cond4 = (((postnumber >= 7980) & (postnumber <= 7981)) | ((postnumber >= 8000) & (postnumber <= 8058)) |
                 ((postnumber >= 8070) & (postnumber <= 8298)) | ((postnumber >= 8322) & (postnumber <= 8322)) |
                 ((postnumber >= 8600) & (postnumber <= 8985)) | ((postnumber >= 9441) & (postnumber <= 9441)) |
                 ((postnumber >= 9444) & (postnumber <= 9444)))

    swm4Cond5 = (((postnumber >= 2485) & (postnumber <= 2542)) | ((postnumber >= 2550) & (postnumber <= 2584)) |
                 ((postnumber >= 6638) & (postnumber <= 6638)) | ((postnumber >= 6689) & (postnumber <= 6690)) |
                 ((postnumber >= 6694) & (postnumber <= 6697)) | ((postnumber >= 6699) & (postnumber <= 6699)) |
                 ((postnumber >= 7002) & (postnumber <= 7009)) | ((postnumber >= 7014) & (postnumber <= 7015)) |
                 ((postnumber >= 7028) & (postnumber <= 7028)) | ((postnumber >= 7032) & (postnumber <= 7033)) |
                 ((postnumber >= 7036) & (postnumber <= 7038)) | ((postnumber >= 7040) & (postnumber <= 7046)) |
                 ((postnumber >= 7048) & (postnumber <= 7070)) | ((postnumber >= 7074) & (postnumber <= 7074)) |
                 ((postnumber >= 7083) & (postnumber <= 7084)) | ((postnumber >= 7200) & (postnumber <= 7338)) |
                 ((postnumber >= 7350) & (postnumber <= 7499)) | ((postnumber >= 7596) & (postnumber <= 7596)))

    swm4Cond6 = (((postnumber >= 4054) & (postnumber <= 4054)) |((postnumber >= 4160) & (postnumber <= 4160)) |
                 ((postnumber >= 4301) & (postnumber <= 4312)) | ((postnumber >= 4314) & (postnumber <= 4724)))

    swm4Cond7 = (((postnumber >= 10) & (postnumber <= 50)) | ((postnumber >= 151) & (postnumber <= 165)) |
                 ((postnumber >= 171) & (postnumber <= 190)) | ((postnumber >= 250) & (postnumber <= 274)) |
                 ((postnumber >= 349) & (postnumber <= 349)) | ((postnumber >= 351) & (postnumber <= 351)) |
                 ((postnumber >= 353) & (postnumber <= 353)) | ((postnumber >= 356) & (postnumber <= 356)) |
                 ((postnumber >= 360) & (postnumber <= 360)) | ((postnumber >= 362) & (postnumber <= 362)) |
                 ((postnumber >= 365) & (postnumber <= 365)) | ((postnumber >= 376) & (postnumber <= 379)) |
                 ((postnumber >= 457) & (postnumber <= 457)) | ((postnumber >= 564) & (postnumber <= 564)) |
                 ((postnumber >= 582) & (postnumber <= 582)) | ((postnumber >= 656) & (postnumber <= 656)) |
                 ((postnumber >= 665) & (postnumber <= 665)) | ((postnumber >= 676) & (postnumber <= 676)) |
                 ((postnumber >= 681) & (postnumber <= 681)) | ((postnumber >= 688) & (postnumber <= 688)) |
                 ((postnumber >= 753) & (postnumber <= 753)) | ((postnumber >= 768) & (postnumber <= 785)) |
                 ((postnumber >= 788) & (postnumber <= 789)) | ((postnumber >= 972) & (postnumber <= 972)) |
                 ((postnumber >= 1291) & (postnumber <= 1295)))

    swm4Cond8 = (((postnumber >= 372) & (postnumber <= 372)) | ((postnumber >= 444) & (postnumber <= 451)) |
                 ((postnumber >= 459) & (postnumber <= 461)) | ((postnumber >= 463) & (postnumber <= 563)) |
                 ((postnumber >= 565) & (postnumber <= 581)) | ((postnumber >= 583) & (postnumber <= 655)) |
                 ((postnumber >= 658) & (postnumber <= 663)) | ((postnumber >= 666) & (postnumber <= 670)) |
                 ((postnumber >= 786) & (postnumber <= 786)) | ((postnumber >= 790) & (postnumber <= 851)) |
                 ((postnumber >= 853) & (postnumber <= 862)) | ((postnumber >= 864) & (postnumber <= 971)) |
                 ((postnumber >= 973) & (postnumber <= 1011)) | ((postnumber >= 1053) & (postnumber <= 1062)) |
                 ((postnumber >= 1064) & (postnumber <= 1064)) | ((postnumber >= 1068) & (postnumber <= 1084)) |
                 ((postnumber >= 1087) & (postnumber <= 1087)))

    swm4Cond9 = (((postnumber >= 3001) & (postnumber <= 3048)) | ((postnumber >= 3054) & (postnumber <= 3055)) |
                 ((postnumber >= 3058) & (postnumber <= 3249)) | ((postnumber >= 3257) & (postnumber <= 3257)) |
                 ((postnumber >= 3275) & (postnumber <= 3277)) | ((postnumber >= 3282) & (postnumber <= 3285)) |
                 ((postnumber >= 3330) & (postnumber <= 3387)) | ((postnumber >= 3535) & (postnumber <= 3536)) |
                 ((postnumber >= 3539) & (postnumber <= 3648)))

    swm4Cond10 = (((postnumber >= 1407) & (postnumber <= 1407)) | ((postnumber >= 1420) & (postnumber <= 1459)) |
                  ((postnumber >= 1501) & (postnumber <= 1798)) | ((postnumber >= 3474) & (postnumber <= 3476)) |
                  ((postnumber >= 3480) & (postnumber <= 3491)))

    swm4Cond11 = (((postnumber >= 5003) & (postnumber <= 5037)) | ((postnumber >= 5050) & (postnumber <= 5099)) |
                  ((postnumber >= 5104) & (postnumber <= 5104)) | ((postnumber >= 5152) & (postnumber <= 5155)) |
                  ((postnumber >= 5218) & (postnumber <= 5286)) | ((postnumber >= 5384) & (postnumber <= 5398)) |
                  ((postnumber >= 5723) & (postnumber <= 5723)))

    swm4Cond12 = (((postnumber >= 5038) & (postnumber <= 5045)) | ((postnumber >= 5101) & (postnumber <= 5101)) |
                  ((postnumber >= 5105) & (postnumber <= 5151)) | ((postnumber >= 5160) & (postnumber <= 5184)) |
                  ((postnumber >= 5291) & (postnumber <= 5382)) | ((postnumber >= 5600) & (postnumber <= 5626)) |
                  ((postnumber >= 5629) & (postnumber <= 5632)) | ((postnumber >= 5650) & (postnumber <= 5659)) |
                  ((postnumber >= 5700) & (postnumber <= 5722)) | ((postnumber >= 5724) & (postnumber <= 5748)) |
                  ((postnumber >= 5802) & (postnumber <= 5994)) | ((postnumber >= 6800) & (postnumber <= 6817)) |
                  ((postnumber >= 6843) & (postnumber <= 6857)) | ((postnumber >= 6861) & (postnumber <= 6912)) |
                  ((postnumber >= 6921) & (postnumber <= 6924)) | ((postnumber >= 6928) & (postnumber <= 6964)) |
                  ((postnumber >= 6967) & (postnumber <= 6983)) | ((postnumber >= 6985) & (postnumber <= 6996)))

    swm4Cond13 = (((postnumber >= 7010) & (postnumber <= 7013)) | ((postnumber >= 7016) & (postnumber <= 7027)) |
                  ((postnumber >= 7029) & (postnumber <= 7031)) | ((postnumber >= 7034) & (postnumber <= 7034)) |
                  ((postnumber >= 7039) & (postnumber <= 7039)) | ((postnumber >= 7047) & (postnumber <= 7047)) |
                  ((postnumber >= 7072) & (postnumber <= 7072)) | ((postnumber >= 7075) & (postnumber <= 7082)) |
                  ((postnumber >= 7088) & (postnumber <= 7099)) | ((postnumber >= 7517) & (postnumber <= 7517)) |
                  ((postnumber >= 7540) & (postnumber <= 7570)))

    swm4Cond14 = (((postnumber >= 3050) & (postnumber <= 3053)) | ((postnumber >= 3056) & (postnumber <= 3057)) |
                  ((postnumber >= 3300) & (postnumber <= 3322)) | ((postnumber >= 3412) & (postnumber <= 3412)) |
                  ((postnumber >= 3519) & (postnumber <= 3519)) | ((postnumber >= 3537) & (postnumber <= 3538)))

    swm4Cond15 = (((postnumber >= 2665) & (postnumber <= 2669)) | ((postnumber >= 6064) & (postnumber <= 6064)) |
                  ((postnumber >= 6094) & (postnumber <= 6095)) | ((postnumber >= 6144) & (postnumber <= 6144)) |
                  ((postnumber >= 6212) & (postnumber <= 6212)) | ((postnumber >= 6215) & (postnumber <= 6215)) |
                  ((postnumber >= 6240) & (postnumber <= 6637)) | ((postnumber >= 6639) & (postnumber <= 6688)) |
                  ((postnumber >= 6693) & (postnumber <= 6693)) | ((postnumber >= 6698) & (postnumber <= 6698)) |
                  ((postnumber >= 7340) & (postnumber <= 7345)))

    swm4Cond16 = (((postnumber >= 55) & (postnumber <= 150)) | ((postnumber >= 166) & (postnumber <= 170)) |
                  ((postnumber >= 191) & (postnumber <= 246)) | ((postnumber >= 313) & (postnumber <= 342)) |
                  ((postnumber >= 350) & (postnumber <= 350)) | ((postnumber >= 352) & (postnumber <= 352)) |
                  ((postnumber >= 354) & (postnumber <= 355)) | ((postnumber >= 357) & (postnumber <= 359)) |
                  ((postnumber >= 361) & (postnumber <= 361)) | ((postnumber >= 363) & (postnumber <= 364)) |
                  ((postnumber >= 366) & (postnumber <= 371)) | ((postnumber >= 373) & (postnumber <= 374)) |
                  ((postnumber >= 452) & (postnumber <= 456)) | ((postnumber >= 458) & (postnumber <= 458)) |
                  ((postnumber >= 462) & (postnumber <= 462)) | ((postnumber >= 657) & (postnumber <= 657)) |
                  ((postnumber >= 664) & (postnumber <= 664)) | ((postnumber >= 671) & (postnumber <= 675)) |
                  ((postnumber >= 677) & (postnumber <= 680)) | ((postnumber >= 682) & (postnumber <= 687)) |
                  ((postnumber >= 689) & (postnumber <= 750)) | ((postnumber >= 852) & (postnumber <= 852)) |
                  ((postnumber >= 863) & (postnumber <= 863)) | ((postnumber >= 1051) & (postnumber <= 1052)) |
                  ((postnumber >= 1063) & (postnumber <= 1063)) | ((postnumber >= 1065) & (postnumber <= 1067)) |
                  ((postnumber >= 1086) & (postnumber <= 1086)) | ((postnumber >= 1088) & (postnumber <= 1290)) |
                  ((postnumber >= 1404) & (postnumber <= 1405)) | ((postnumber >= 1410) & (postnumber <= 1417)))

    swm4Cond17 = (((postnumber >= 8063) & (postnumber <= 8064)) | ((postnumber >= 8300) & (postnumber <= 8320)) |
                  ((postnumber >= 8323) & (postnumber <= 8591)) | ((postnumber >= 9000) & (postnumber <= 9059)) |
                  ((postnumber >= 9062) & (postnumber <= 9068)) | ((postnumber >= 9100) & (postnumber <= 9107)) |
                  ((postnumber >= 9153) & (postnumber <= 9153)) | ((postnumber >= 9200) & (postnumber <= 9440)) |
                  ((postnumber >= 9442) & (postnumber <= 9443)) | ((postnumber >= 9450) & (postnumber <= 9450)) |
                  ((postnumber >= 9475) & (postnumber <= 9498)))

    swm4Cond18 = (((postnumber >= 275) & (postnumber <= 312)) | ((postnumber >= 375) & (postnumber <= 375)) |
                  ((postnumber >= 380) & (postnumber <= 440)) | ((postnumber >= 751) & (postnumber <= 752)) |
                  ((postnumber >= 754) & (postnumber <= 767)) | ((postnumber >= 787) & (postnumber <= 787)) |
                  ((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3400) & (postnumber <= 3410)) |
                  ((postnumber >= 3414) & (postnumber <= 3472)) | ((postnumber >= 3477) & (postnumber <= 3478)) |
                  ((postnumber >= 3501) & (postnumber <= 3518)) | ((postnumber >= 3524) & (postnumber <= 3526)) |
                  ((postnumber >= 3529) & (postnumber <= 3534)))

    swm4Cond19 = (((postnumber >= 2320) & (postnumber <= 2320)) | ((postnumber >= 2350) & (postnumber <= 2391)) |
                  ((postnumber >= 2600) & (postnumber <= 2608)) | ((postnumber >= 2610) & (postnumber <= 2610)) |
                  ((postnumber >= 2612) & (postnumber <= 2612)) | ((postnumber >= 2616) & (postnumber <= 2617)) |
                  ((postnumber >= 2625) & (postnumber <= 2625)) | ((postnumber >= 2630) & (postnumber <= 2663)) |
                  ((postnumber >= 2670) & (postnumber <= 2694)) | ((postnumber >= 2711) & (postnumber <= 2985)) |
                  ((postnumber >= 3520) & (postnumber <= 3522)) | ((postnumber >= 3528) & (postnumber <= 3528)))

    swm4Cond20 = (((postnumber >= 3251) & (postnumber <= 3256)) | ((postnumber >= 3258) & (postnumber <= 3274)) |
                  ((postnumber >= 3280) & (postnumber <= 3280)) | ((postnumber >= 3290) & (postnumber <= 3296)) |
                  ((postnumber >= 3650) & (postnumber <= 3999)) | ((postnumber >= 4730) & (postnumber <= 4994)))

    swm4Cond21 = (((postnumber >= 2695) & (postnumber <= 2695)) | ((postnumber >= 6001) & (postnumber <= 6063)) |
                  ((postnumber >= 6065) & (postnumber <= 6092)) | ((postnumber >= 6096) & (postnumber <= 6143)) |
                  ((postnumber >= 6146) & (postnumber <= 6210)) | ((postnumber >= 6213) & (postnumber <= 6214)) |
                  ((postnumber >= 6216) & (postnumber <= 6239)) | ((postnumber >= 6700) & (postnumber <= 6799)) |
                  ((postnumber >= 6818) & (postnumber <= 6841)) | ((postnumber >= 6858) & (postnumber <= 6859)) |
                  ((postnumber >= 6914) & (postnumber <= 6919)) | ((postnumber >= 6926) & (postnumber <= 6927)) |
                  ((postnumber >= 6966) & (postnumber <= 6966)) | ((postnumber >= 6984) & (postnumber <= 6984)))

    swm4Cond22 = (((postnumber >= 7100) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7514)) |
                  ((postnumber >= 7519) & (postnumber <= 7533)) | ((postnumber >= 7580) & (postnumber <= 7591)) |
                  ((postnumber >= 7600) & (postnumber <= 7977)) | ((postnumber >= 7982) & (postnumber <= 7994)))

    swm4Cond23 = (((postnumber >= 1400) & (postnumber <= 1403)) | ((postnumber >= 1406) & (postnumber <= 1406)) |
                  ((postnumber >= 1408) & (postnumber <= 1409)) | ((postnumber >= 1470) & (postnumber <= 1488)) |
                  ((postnumber >= 1800) & (postnumber <= 2027)) | ((postnumber >= 2040) & (postnumber <= 2054)) |
                  ((postnumber >= 2067) & (postnumber <= 2069)) | ((postnumber >= 2150) & (postnumber <= 2170)))

    swm4Cond24 = (((postnumber >= 4152) & (postnumber <= 4153)) | ((postnumber >= 4157) & (postnumber <= 4158)) |
                  ((postnumber >= 4200) & (postnumber <= 4299)) | ((postnumber >= 5200) & (postnumber <= 5217)) |
                  ((postnumber >= 5399) & (postnumber <= 5598)) | ((postnumber >= 5627) & (postnumber <= 5628)) |
                  ((postnumber >= 5635) & (postnumber <= 5649)) | ((postnumber >= 5680) & (postnumber <= 5696)) |
                  ((postnumber >= 5750) & (postnumber <= 5787)))

    conditionList = [swm4Cond1, swm4Cond2, swm4Cond3, swm4Cond4, swm4Cond5, swm4Cond6, swm4Cond7, swm4Cond8,
                     swm4Cond9, swm4Cond10, swm4Cond11, swm4Cond12, swm4Cond13, swm4Cond14, swm4Cond15, swm4Cond16,
                     swm4Cond17, swm4Cond18, swm4Cond19, swm4Cond20, swm4Cond21, swm4Cond22, swm4Cond23, swm4Cond24]

    def conditioncheck(conditions):
        swm4 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                swm4 = index + 1
        return swm4

    swm4 = conditioncheck(conditionList)

    return swm4

def swm5(postnumber):
    swm5Cond1 = (((postnumber >= 2030 ) & (postnumber <= 2034)) | ((postnumber >= 2055 ) & (postnumber <= 2061)) |
                  ((postnumber >= 2070 ) & (postnumber <= 2134)) | ((postnumber >= 2201 ) & (postnumber <= 2482)) |
                  ((postnumber >= 2601 ) & (postnumber <= 2663)) | ((postnumber >= 2670 ) & (postnumber <= 2985)) |
                  ((postnumber >= 3520 ) & (postnumber <= 3522)) | ((postnumber >= 3528 ) & (postnumber <= 3528)))

    swm5Cond2 = (((postnumber >= 4001 ) & (postnumber <= 4053)) | ((postnumber >= 4055 ) & (postnumber <= 4150)) |
                 ((postnumber >= 4156 ) & (postnumber <= 4156)) | ((postnumber >= 4163 ) & (postnumber <= 4198)) |
                 ((postnumber >= 4313 ) & (postnumber <= 4313)))

    swm5Cond3 = (((postnumber >= 7980 ) & (postnumber <= 7981)) | ((postnumber >= 8000 ) & (postnumber <= 8056)) |
                 ((postnumber >= 8071 ) & (postnumber <= 8108)) | ((postnumber >= 8114 ) & (postnumber <= 8136)) |
                 ((postnumber >= 8157 ) & (postnumber <= 8159)) | ((postnumber >= 8168 ) & (postnumber <= 8184)) |
                 ((postnumber >= 8186 ) & (postnumber <= 8256)) | ((postnumber >= 8264 ) & (postnumber <= 8266)) |
                 ((postnumber >= 8275 ) & (postnumber <= 8286)) | ((postnumber >= 8289 ) & (postnumber <= 8298)) |
                 ((postnumber >= 8501 ) & (postnumber <= 8522)) | ((postnumber >= 8530 ) & (postnumber <= 8531)) |
                 ((postnumber >= 8536 ) & (postnumber <= 8536)) | ((postnumber >= 8601 ) & (postnumber <= 8608)) |
                 ((postnumber >= 8617 ) & (postnumber <= 8617)) | ((postnumber >= 8642 ) & (postnumber <= 8642)) |
                 ((postnumber >= 8647 ) & (postnumber <= 8647)) | ((postnumber >= 8658 ) & (postnumber <= 8661)) |
                 ((postnumber >= 8664 ) & (postnumber <= 8664)) | ((postnumber >= 8672 ) & (postnumber <= 8672)) |
                 ((postnumber >= 8690 ) & (postnumber <= 8691)) | ((postnumber >= 8720 ) & (postnumber <= 8770)) |
                 ((postnumber >= 8813 ) & (postnumber <= 8842)) | ((postnumber >= 8854 ) & (postnumber <= 8870)) |
                 ((postnumber >= 8976 ) & (postnumber <= 9024)) | ((postnumber >= 9037 ) & (postnumber <= 9038)) |
                 ((postnumber >= 9100 ) & (postnumber <= 9100)) | ((postnumber >= 9104 ) & (postnumber <= 9104)) |
                 ((postnumber >= 9107 ) & (postnumber <= 9107)) | ((postnumber >= 9403 ) & (postnumber <= 9406)) |
                 ((postnumber >= 9409 ) & (postnumber <= 9419)) | ((postnumber >= 9439 ) & (postnumber <= 9441)) |
                 ((postnumber >= 9444 ) & (postnumber <= 9444)))

    swm5Cond4 = (((postnumber >= 2485 ) & (postnumber <= 2584)) | ((postnumber >= 6689 ) & (postnumber <= 6690)) |
                 ((postnumber >= 6694 ) & (postnumber <= 6699)) | ((postnumber >= 7011 ) & (postnumber <= 7011)) |
                 ((postnumber >= 7014 ) & (postnumber <= 7016)) | ((postnumber >= 7028 ) & (postnumber <= 7028)) |
                 ((postnumber >= 7030 ) & (postnumber <= 7030)) | ((postnumber >= 7032 ) & (postnumber <= 7033)) |
                 ((postnumber >= 7036 ) & (postnumber <= 7046)) | ((postnumber >= 7048 ) & (postnumber <= 7070)) |
                 ((postnumber >= 7074 ) & (postnumber <= 7074)) | ((postnumber >= 7083 ) & (postnumber <= 7083)) |
                 ((postnumber >= 7100 ) & (postnumber <= 7338)) | ((postnumber >= 7350 ) & (postnumber <= 7496)) |
                 ((postnumber >= 7510 ) & (postnumber <= 7510)) | ((postnumber >= 7519 ) & (postnumber <= 7533)) |
                 ((postnumber >= 7580 ) & (postnumber <= 7977)) | ((postnumber >= 7982 ) & (postnumber <= 7994)))

    swm5Cond5 = (((postnumber >= 4054 ) & (postnumber <= 4054)) | ((postnumber >= 4160 ) & (postnumber <= 4160)) |
                 ((postnumber >= 4301 ) & (postnumber <= 4312)) | ((postnumber >= 4314 ) & (postnumber <= 4720)))

    swm5Cond6 = (((postnumber >= 10 ) & (postnumber <= 60)) | ((postnumber >= 151 ) & (postnumber <= 165)) |
                 ((postnumber >= 171 ) & (postnumber <= 190)) | ((postnumber >= 230 ) & (postnumber <= 274)) |
                 ((postnumber >= 349 ) & (postnumber <= 349)) | ((postnumber >= 356 ) & (postnumber <= 356)) |
                 ((postnumber >= 360 ) & (postnumber <= 360)) | ((postnumber >= 362 ) & (postnumber <= 362)) |
                 ((postnumber >= 365 ) & (postnumber <= 365)) | ((postnumber >= 374 ) & (postnumber <= 374)) |
                 ((postnumber >= 376 ) & (postnumber <= 379)) | ((postnumber >= 570 ) & (postnumber <= 570)) |
                 ((postnumber >= 582 ) & (postnumber <= 582)) | ((postnumber >= 656 ) & (postnumber <= 656)) |
                 ((postnumber >= 665 ) & (postnumber <= 665)) | ((postnumber >= 676 ) & (postnumber <= 677)) |
                 ((postnumber >= 681 ) & (postnumber <= 681)) | ((postnumber >= 688 ) & (postnumber <= 688)) |
                 ((postnumber >= 752 ) & (postnumber <= 753)) | ((postnumber >= 768 ) & (postnumber <= 784)) |
                 ((postnumber >= 1290 ) & (postnumber <= 1295)))

    swm5Cond7 = (((postnumber >= 3001 ) & (postnumber <= 3249)) | ((postnumber >= 3275 ) & (postnumber <= 3277)) |
                 ((postnumber >= 3282 ) & (postnumber <= 3282)) | ((postnumber >= 3300 ) & (postnumber <= 3371)) |
                 ((postnumber >= 3535 ) & (postnumber <= 3537)) | ((postnumber >= 3539 ) & (postnumber <= 3648)))

    swm5Cond8 = (((postnumber >= 1407 ) & (postnumber <= 1407)) | ((postnumber >= 1420 ) & (postnumber <= 1458)) |
                 ((postnumber >= 1501 ) & (postnumber <= 1798)) | ((postnumber >= 3474 ) & (postnumber <= 3476)) |
                 ((postnumber >= 3480 ) & (postnumber <= 3490)))

    swm5Cond9 = (((postnumber >= 5003 ) & (postnumber <= 5036)) | ((postnumber >= 5050 ) & (postnumber <= 5098)) |
                 ((postnumber >= 5151 ) & (postnumber <= 5155)) | ((postnumber >= 5221 ) & (postnumber <= 5261)) |
                 ((postnumber >= 5263 ) & (postnumber <= 5299)) | ((postnumber >= 5360 ) & (postnumber <= 5360)) |
                 ((postnumber >= 5384 ) & (postnumber <= 5399)))

    swm5Cond10 = (((postnumber >= 275 ) & (postnumber <= 287)) | ((postnumber >= 375 ) & (postnumber <= 375)) |
                   ((postnumber >= 380 ) & (postnumber <= 383)) | ((postnumber >= 701 ) & (postnumber <= 751)) |
                   ((postnumber >= 754 ) & (postnumber <= 767)) | ((postnumber >= 1300 ) & (postnumber <= 1397)) |
                   ((postnumber >= 3400 ) & (postnumber <= 3472)) | ((postnumber >= 3477 ) & (postnumber <= 3478)) |
                   ((postnumber >= 3501 ) & (postnumber <= 3519)) | ((postnumber >= 3524 ) & (postnumber <= 3526)) |
                   ((postnumber >= 3529 ) & (postnumber <= 3534)) | ((postnumber >= 3538 ) & (postnumber <= 3538)))

    swm5Cond11 = (((postnumber >= 5038 ) & (postnumber <= 5045)) | ((postnumber >= 5101 ) & (postnumber <= 5148)) |
                  ((postnumber >= 5160 ) & (postnumber <= 5184)) | ((postnumber >= 5262 ) & (postnumber <= 5262)) |
                  ((postnumber >= 5300 ) & (postnumber <= 5358)) | ((postnumber >= 5363 ) & (postnumber <= 5382)) |
                  ((postnumber >= 5600 ) & (postnumber <= 5620)) | ((postnumber >= 5630 ) & (postnumber <= 5632)) |
                  ((postnumber >= 5650 ) & (postnumber <= 5658)) | ((postnumber >= 5700 ) & (postnumber <= 5748)) |
                  ((postnumber >= 5802 ) & (postnumber <= 5994)) | ((postnumber >= 6800 ) & (postnumber <= 6819)) |
                  ((postnumber >= 6841 ) & (postnumber <= 6996)))

    swm5Cond12 = (((postnumber >= 2665 ) & (postnumber <= 2669)) | ((postnumber >= 6001 ) & (postnumber <= 6688)) |
                  ((postnumber >= 6693 ) & (postnumber <= 6693)) | ((postnumber >= 6700 ) & (postnumber <= 6799)) |
                  ((postnumber >= 6821 ) & (postnumber <= 6829)) | ((postnumber >= 7340 ) & (postnumber <= 7345)))

    swm5Cond13 = (((postnumber >= 7002 ) & (postnumber <= 7010)) | ((postnumber >= 7012 ) & (postnumber <= 7013)) |
                  ((postnumber >= 7018 ) & (postnumber <= 7027)) | ((postnumber >= 7029 ) & (postnumber <= 7029)) |
                  ((postnumber >= 7031 ) & (postnumber <= 7031)) | ((postnumber >= 7034 ) & (postnumber <= 7034)) |
                  ((postnumber >= 7047 ) & (postnumber <= 7047)) | ((postnumber >= 7072 ) & (postnumber <= 7072)) |
                  ((postnumber >= 7075 ) & (postnumber <= 7082)) | ((postnumber >= 7088 ) & (postnumber <= 7099)) |
                  ((postnumber >= 7500 ) & (postnumber <= 7509)) | ((postnumber >= 7517 ) & (postnumber <= 7517)) |
                  ((postnumber >= 7540 ) & (postnumber <= 7570)))

    swm5Cond14 = (((postnumber >= 101 ) & (postnumber <= 150)) | ((postnumber >= 166 ) & (postnumber <= 170)) |
                  ((postnumber >= 191 ) & (postnumber <= 216)) | ((postnumber >= 301 ) & (postnumber <= 340)) |
                  ((postnumber >= 350 ) & (postnumber <= 355)) | ((postnumber >= 357 ) & (postnumber <= 359)) |
                  ((postnumber >= 361 ) & (postnumber <= 361)) | ((postnumber >= 363 ) & (postnumber <= 364)) |
                  ((postnumber >= 366 ) & (postnumber <= 371)) | ((postnumber >= 373 ) & (postnumber <= 373)) |
                  ((postnumber >= 452 ) & (postnumber <= 458)) | ((postnumber >= 664 ) & (postnumber <= 664)) |
                  ((postnumber >= 669 ) & (postnumber <= 675)) | ((postnumber >= 678 ) & (postnumber <= 680)) |
                  ((postnumber >= 682 ) & (postnumber <= 687)) | ((postnumber >= 689 ) & (postnumber <= 694)) |
                  ((postnumber >= 852 ) & (postnumber <= 852)) | ((postnumber >= 1001 ) & (postnumber <= 1051)) |
                  ((postnumber >= 1062 ) & (postnumber <= 1063)) | ((postnumber >= 1065 ) & (postnumber <= 1067)) |
                  ((postnumber >= 1084 ) & (postnumber <= 1286)) | ((postnumber >= 1403 ) & (postnumber <= 1405)) |
                  ((postnumber >= 1410 ) & (postnumber <= 1417)))

    swm5Cond15 = (((postnumber >= 8058 ) & (postnumber <= 8064)) | ((postnumber >= 8110 ) & (postnumber <= 8110)) |
                  ((postnumber >= 8138 ) & (postnumber <= 8151)) | ((postnumber >= 8160 ) & (postnumber <= 8161)) |
                  ((postnumber >= 8185 ) & (postnumber <= 8185)) | ((postnumber >= 8260 ) & (postnumber <= 8261)) |
                  ((postnumber >= 8270 ) & (postnumber <= 8274)) | ((postnumber >= 8288 ) & (postnumber <= 8288)) |
                  ((postnumber >= 8300 ) & (postnumber <= 8493)) | ((postnumber >= 8523 ) & (postnumber <= 8523)) |
                  ((postnumber >= 8533 ) & (postnumber <= 8535)) | ((postnumber >= 8539 ) & (postnumber <= 8591)) |
                  ((postnumber >= 8610 ) & (postnumber <= 8616)) | ((postnumber >= 8618 ) & (postnumber <= 8641)) |
                  ((postnumber >= 8643 ) & (postnumber <= 8646)) | ((postnumber >= 8648 ) & (postnumber <= 8657)) |
                  ((postnumber >= 8663 ) & (postnumber <= 8663)) | ((postnumber >= 8665 ) & (postnumber <= 8665)) |
                  ((postnumber >= 8680 ) & (postnumber <= 8686)) | ((postnumber >= 8700 ) & (postnumber <= 8701)) |
                  ((postnumber >= 8800 ) & (postnumber <= 8805)) | ((postnumber >= 8844 ) & (postnumber <= 8852)) |
                  ((postnumber >= 8880 ) & (postnumber <= 8961)) | ((postnumber >= 9027 ) & (postnumber <= 9034)) |
                  ((postnumber >= 9040 ) & (postnumber <= 9080)) | ((postnumber >= 9103 ) & (postnumber <= 9103)) |
                  ((postnumber >= 9106 ) & (postnumber <= 9106)) | ((postnumber >= 9110 ) & (postnumber <= 9402)) |
                  ((postnumber >= 9407 ) & (postnumber <= 9408)) | ((postnumber >= 9420 ) & (postnumber <= 9436)) |
                  ((postnumber >= 9442 ) & (postnumber <= 9443)) | ((postnumber >= 9445 ) & (postnumber <= 9991)))

    swm5Cond16 = (((postnumber >= 3251 ) & (postnumber <= 3274)) | ((postnumber >= 3280 ) & (postnumber <= 3280)) |
                  ((postnumber >= 3290 ) & (postnumber <= 3296)) | ((postnumber >= 3650 ) & (postnumber <= 3999)) |
                  ((postnumber >= 4724 ) & (postnumber <= 4994)))

    swm5Cond17 = (((postnumber >= 372 ) & (postnumber <= 372)) | ((postnumber >= 401 ) & (postnumber <= 451)) |
                  ((postnumber >= 459 ) & (postnumber <= 569)) | ((postnumber >= 571 ) & (postnumber <= 581)) |
                  ((postnumber >= 583 ) & (postnumber <= 655)) | ((postnumber >= 657 ) & (postnumber <= 663)) |
                  ((postnumber >= 666 ) & (postnumber <= 668)) | ((postnumber >= 785 ) & (postnumber <= 851)) |
                  ((postnumber >= 853 ) & (postnumber <= 988)) | ((postnumber >= 1052 ) & (postnumber <= 1061)) |
                  ((postnumber >= 1064 ) & (postnumber <= 1064)) | ((postnumber >= 1068 ) & (postnumber <= 1083)))

    swm5Cond18 = (((postnumber >= 1400 ) & (postnumber <= 1402)) | ((postnumber >= 1406 ) & (postnumber <= 1406)) |
                  ((postnumber >= 1408 ) & (postnumber <= 1409)) | ((postnumber >= 1470 ) & (postnumber <= 1488)) |
                  ((postnumber >= 1800 ) & (postnumber <= 2027)) | ((postnumber >= 2040 ) & (postnumber <= 2053)) |
                  ((postnumber >= 2063 ) & (postnumber <= 2069)) | ((postnumber >= 2150 ) & (postnumber <= 2170)))

    swm5Cond19 = (((postnumber >= 4152 ) & (postnumber <= 4153)) | ((postnumber >= 4158 ) & (postnumber <= 4158)) |
                  ((postnumber >= 4200 ) & (postnumber <= 4299)) | ((postnumber >= 5200 ) & (postnumber <= 5218)) |
                  ((postnumber >= 5401 ) & (postnumber <= 5598)) | ((postnumber >= 5626 ) & (postnumber <= 5629)) |
                  ((postnumber >= 5635 ) & (postnumber <= 5649)) | ((postnumber >= 5680 ) & (postnumber <= 5696)) |
                  ((postnumber >= 5750 ) & (postnumber <= 5787)))

    conditionList = [swm5Cond1, swm5Cond2, swm5Cond3, swm5Cond4, swm5Cond5, swm5Cond6, swm5Cond7, swm5Cond8,
                     swm5Cond9, swm5Cond10, swm5Cond11, swm5Cond12, swm5Cond13, swm5Cond14, swm5Cond15, swm5Cond16,
                     swm5Cond17, swm5Cond18, swm5Cond19]

    def conditioncheck(conditions):
        swm5 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                swm5 = index + 1
        return swm5

    swm5 = conditioncheck(conditionList)

    return swm5

def tin3(postnumber):
    tin3Cond1 = (((postnumber >= 4395) & (postnumber <= 4438)) | ((postnumber >= 4465) & (postnumber <= 4994)))

    tin3Cond2 = (((postnumber >= 277) & (postnumber <= 278)) | ((postnumber >= 279) & (postnumber <= 279)) |
                 ((postnumber >= 282) & (postnumber <= 286)) | ((postnumber >= 373) & (postnumber <= 376)) |
                 ((postnumber >= 378) & (postnumber <= 378)) | ((postnumber >= 381) & (postnumber <= 381)) |
                 ((postnumber >= 383) & (postnumber <= 383)) | ((postnumber >= 751) & (postnumber <= 751)) |
                 ((postnumber >= 753) & (postnumber <= 753)) | ((postnumber >= 756) & (postnumber <= 758)) |
                 ((postnumber >= 768) & (postnumber <= 768)) | ((postnumber >= 771) & (postnumber <= 771)) |
                 ((postnumber >= 773) & (postnumber <= 773)) | ((postnumber >= 776) & (postnumber <= 776)) |
                 ((postnumber >= 784) & (postnumber <= 784)) | ((postnumber >= 851) & (postnumber <= 853)) |
                 ((postnumber >= 855) & (postnumber <= 855)) | ((postnumber >= 858) & (postnumber <= 860)) |
                 ((postnumber >= 862) & (postnumber <= 862)) | ((postnumber >= 864) & (postnumber <= 864)) |
                 ((postnumber >= 1300) & (postnumber <= 1397)) | ((postnumber >= 3420) & (postnumber <= 3420)))

    tin3Cond3 = (((postnumber >= 1400) & (postnumber <= 1400)) | ((postnumber >= 1404) & (postnumber <= 1408)) |
                ((postnumber >= 1410) & (postnumber <= 1410)) | ((postnumber >= 1412) & (postnumber <= 1415)) |
                ((postnumber >= 1430) & (postnumber <= 1430)) | ((postnumber >= 1440) & (postnumber <= 1440)) |
                ((postnumber >= 1445) & (postnumber <= 1450)) | ((postnumber >= 1452) & (postnumber <= 1458)) |
                ((postnumber >= 1470) & (postnumber <= 1470)) | ((postnumber >= 1472) & (postnumber <= 1481)) |
                ((postnumber >= 1540) & (postnumber <= 1540)) | ((postnumber >= 1550) & (postnumber <= 1555)) |
                ((postnumber >= 1900) & (postnumber <= 1914)) | ((postnumber >= 1921) & (postnumber <= 1921)) |
                ((postnumber >= 1927) & (postnumber <= 1927)) | ((postnumber >= 1941) & (postnumber <= 1941)) |
                ((postnumber >= 2000) & (postnumber <= 2015)) | ((postnumber >= 2019) & (postnumber <= 2027)) |
                ((postnumber >= 2031) & (postnumber <= 2031)) | ((postnumber >= 2033) & (postnumber <= 2033)) |
                ((postnumber >= 2041) & (postnumber <= 2041)) | ((postnumber >= 2051) & (postnumber <= 2051)) |
                ((postnumber >= 2054) & (postnumber <= 2054)) | ((postnumber >= 2056) & (postnumber <= 2066)) |
                ((postnumber >= 2068) & (postnumber <= 2068)) | ((postnumber >= 2071) & (postnumber <= 2071)) |
                ((postnumber >= 2073) & (postnumber <= 2074)) | ((postnumber >= 2081) & (postnumber <= 2081)) |
                ((postnumber >= 2091) & (postnumber <= 2091)) | ((postnumber >= 2101) & (postnumber <= 2101)) |
                ((postnumber >= 2114) & (postnumber <= 2116)) | ((postnumber >= 2134) & (postnumber <= 2134)) |
                ((postnumber >= 2151) & (postnumber <= 2151)))

    tin3Cond4 = (((postnumber >= 3001) & (postnumber <= 3058)) | ((postnumber >= 3300) & (postnumber <= 3414)) |
                 ((postnumber >= 3421) & (postnumber <= 3519)) | ((postnumber >= 3521) & (postnumber <= 3521)) |
                 ((postnumber >= 3524) & (postnumber <= 3526)) | ((postnumber >= 3529) & (postnumber <= 3648)) |
                 ((postnumber >= 3658) & (postnumber <= 3658)))

    tin3Cond5 = (((postnumber >= 5003) & (postnumber <= 5004)) |((postnumber >= 5006) & (postnumber <= 5008)) |
                ((postnumber >= 5011) & (postnumber <= 5017)) | ((postnumber >= 5034) & (postnumber <= 5036)) |
                ((postnumber >= 5038) & (postnumber <= 5039)) | ((postnumber >= 5106) & (postnumber <= 5106)) |
                ((postnumber >= 5109) & (postnumber <= 5109)) | ((postnumber >= 5113) & (postnumber <= 5113)) |
                ((postnumber >= 5115) & (postnumber <= 5116)) | ((postnumber >= 5118) & (postnumber <= 5119)) |
                ((postnumber >= 5124) & (postnumber <= 5134)) | ((postnumber >= 5136) & (postnumber <= 5136)) |
                ((postnumber >= 5160) & (postnumber <= 5163)) | ((postnumber >= 5165) & (postnumber <= 5165)) |
                ((postnumber >= 5171) & (postnumber <= 5176)) | ((postnumber >= 5178) & (postnumber <= 5184)) |
                ((postnumber >= 5260) & (postnumber <= 5260)) | ((postnumber >= 5262) & (postnumber <= 5262)) |
                ((postnumber >= 5265) & (postnumber <= 5265)) | ((postnumber >= 5268) & (postnumber <= 5286)) |
                ((postnumber >= 5300) & (postnumber <= 5303)) | ((postnumber >= 5305) & (postnumber <= 5305)) |
                ((postnumber >= 5308) & (postnumber <= 5314)) | ((postnumber >= 5326) & (postnumber <= 5326)) |
                ((postnumber >= 5334) & (postnumber <= 5334)) | ((postnumber >= 5336) & (postnumber <= 5337)) |
                ((postnumber >= 5347) & (postnumber <= 5357)) | ((postnumber >= 5360) & (postnumber <= 5363)) |
                ((postnumber >= 5379) & (postnumber <= 5379)) | ((postnumber >= 5382) & (postnumber <= 5382)) |
                ((postnumber >= 5541) & (postnumber <= 5541)) | ((postnumber >= 5546) & (postnumber <= 5546)) |
                ((postnumber >= 5575) & (postnumber <= 5575)) | ((postnumber >= 5578) & (postnumber <= 5578)) |
                ((postnumber >= 5586) & (postnumber <= 5589)) | ((postnumber >= 5594) & (postnumber <= 5595)) |
                ((postnumber >= 5598) & (postnumber <= 5598)) | ((postnumber >= 5601) & (postnumber <= 5605)) |
                ((postnumber >= 5612) & (postnumber <= 5612)) | ((postnumber >= 5626) & (postnumber <= 5626)) |
                ((postnumber >= 5629) & (postnumber <= 5629)) | ((postnumber >= 5646) & (postnumber <= 5646)) |
                ((postnumber >= 5649) & (postnumber <= 5649)) | ((postnumber >= 5658) & (postnumber <= 5659)) |
                ((postnumber >= 5681) & (postnumber <= 5682)) | ((postnumber >= 5687) & (postnumber <= 5687)) |
                ((postnumber >= 5695) & (postnumber <= 5695)) | ((postnumber >= 5700) & (postnumber <= 5718)) |
                ((postnumber >= 5721) & (postnumber <= 5729)) | ((postnumber >= 5731) & (postnumber <= 5734)) |
                ((postnumber >= 5741) & (postnumber <= 5742)) | ((postnumber >= 5748) & (postnumber <= 5748)) |
                ((postnumber >= 5773) & (postnumber <= 5773)) | ((postnumber >= 5778) & (postnumber <= 5778)) |
                ((postnumber >= 5780) & (postnumber <= 5780)) | ((postnumber >= 5784) & (postnumber <= 5852)) |
                ((postnumber >= 5854) & (postnumber <= 5857)) | ((postnumber >= 5859) & (postnumber <= 5961)) |
                ((postnumber >= 5966) & (postnumber <= 5994)))

    tin3Cond6 = (((postnumber >= 5005) & (postnumber <= 5005)) | ((postnumber >= 5009) & (postnumber <= 5010)) |
                ((postnumber >= 5018) & (postnumber <= 5033)) | ((postnumber >= 5037) & (postnumber <= 5037)) |
                ((postnumber >= 5041) & (postnumber <= 5105)) | ((postnumber >= 5107) & (postnumber <= 5108)) |
                ((postnumber >= 5111) & (postnumber <= 5111)) | ((postnumber >= 5114) & (postnumber <= 5114)) |
                ((postnumber >= 5117) & (postnumber <= 5117)) | ((postnumber >= 5121) & (postnumber <= 5122)) |
                ((postnumber >= 5135) & (postnumber <= 5135)) | ((postnumber >= 5137) & (postnumber <= 5155)) |
                ((postnumber >= 5164) & (postnumber <= 5164)) | ((postnumber >= 5170) & (postnumber <= 5170)) |
                ((postnumber >= 5177) & (postnumber <= 5177)) | ((postnumber >= 5200) & (postnumber <= 5259)) |
                ((postnumber >= 5261) & (postnumber <= 5261)) | ((postnumber >= 5263) & (postnumber <= 5264)) |
                ((postnumber >= 5267) & (postnumber <= 5267)) | ((postnumber >= 5291) & (postnumber <= 5299)) |
                ((postnumber >= 5304) & (postnumber <= 5304)) | ((postnumber >= 5306) & (postnumber <= 5307)) |
                ((postnumber >= 5315) & (postnumber <= 5325)) | ((postnumber >= 5327) & (postnumber <= 5333)) |
                ((postnumber >= 5335) & (postnumber <= 5335)) | ((postnumber >= 5341) & (postnumber <= 5346)) |
                ((postnumber >= 5358) & (postnumber <= 5358)) | ((postnumber >= 5371) & (postnumber <= 5378)) |
                ((postnumber >= 5380) & (postnumber <= 5381)) | ((postnumber >= 5384) & (postnumber <= 5499)) |
                ((postnumber >= 5550) & (postnumber <= 5559)) | ((postnumber >= 5600) & (postnumber <= 5600)) |
                ((postnumber >= 5610) & (postnumber <= 5610)) | ((postnumber >= 5614) & (postnumber <= 5620)) |
                ((postnumber >= 5627) & (postnumber <= 5628)) | ((postnumber >= 5630) & (postnumber <= 5645)) |
                ((postnumber >= 5647) & (postnumber <= 5647)) | ((postnumber >= 5650) & (postnumber <= 5652)) |
                ((postnumber >= 5680) & (postnumber <= 5680)) | ((postnumber >= 5683) & (postnumber <= 5685)) |
                ((postnumber >= 5690) & (postnumber <= 5694)) | ((postnumber >= 5696) & (postnumber <= 5696)) |
                ((postnumber >= 5719) & (postnumber <= 5719)) | ((postnumber >= 5730) & (postnumber <= 5730)) |
                ((postnumber >= 5736) & (postnumber <= 5736)) | ((postnumber >= 5750) & (postnumber <= 5770)) |
                ((postnumber >= 5776) & (postnumber <= 5777)) | ((postnumber >= 5779) & (postnumber <= 5779)) |
                ((postnumber >= 5781) & (postnumber <= 5783)) | ((postnumber >= 5853) & (postnumber <= 5853)) |
                ((postnumber >= 5858) & (postnumber <= 5858)))

    tin3Cond7 = (((postnumber >= 2301) & (postnumber <= 2435)) | ((postnumber >= 2437) & (postnumber <= 2487)) |
                ((postnumber >= 2501) & (postnumber <= 2501)) | ((postnumber >= 2544) & (postnumber <= 2544)) |
                ((postnumber >= 2555) & (postnumber <= 2555)) | ((postnumber >= 2582) & (postnumber <= 2582)) |
                ((postnumber >= 2600) & (postnumber <= 2720)) | ((postnumber >= 2801) & (postnumber <= 2827)) |
                ((postnumber >= 2831) & (postnumber <= 2839)) | ((postnumber >= 2851) & (postnumber <= 2858)) |
                ((postnumber >= 2862) & (postnumber <= 2862)) | ((postnumber >= 2866) & (postnumber <= 2868)) |
                ((postnumber >= 2879) & (postnumber <= 2879)) | ((postnumber >= 2881) & (postnumber <= 2882)))

    tin3Cond8 = (((postnumber >= 1482) & (postnumber <= 1482)) | ((postnumber >= 1488) & (postnumber <= 1488)) |
                ((postnumber >= 1920) & (postnumber <= 1920)) | ((postnumber >= 1923) & (postnumber <= 1925)) |
                ((postnumber >= 1929) & (postnumber <= 1940)) | ((postnumber >= 1945) & (postnumber <= 1945)) |
                ((postnumber >= 1954) & (postnumber <= 1970)) | ((postnumber >= 2016) & (postnumber <= 2016)) |
                ((postnumber >= 2030) & (postnumber <= 2030)) | ((postnumber >= 2032) & (postnumber <= 2032)) |
                ((postnumber >= 2034) & (postnumber <= 2040)) | ((postnumber >= 2050) & (postnumber <= 2050)) |
                ((postnumber >= 2052) & (postnumber <= 2053)) | ((postnumber >= 2055) & (postnumber <= 2055)) |
                ((postnumber >= 2067) & (postnumber <= 2067)) | ((postnumber >= 2069) & (postnumber <= 2070)) |
                ((postnumber >= 2072) & (postnumber <= 2072)) | ((postnumber >= 2080) & (postnumber <= 2080)) |
                ((postnumber >= 2090) & (postnumber <= 2090)) | ((postnumber >= 2092) & (postnumber <= 2100)) |
                ((postnumber >= 2110) & (postnumber <= 2110)) | ((postnumber >= 2120) & (postnumber <= 2133)) |
                ((postnumber >= 2150) & (postnumber <= 2150)) | ((postnumber >= 2160) & (postnumber <= 2283)) |
                ((postnumber >= 2436) & (postnumber <= 2436)) | ((postnumber >= 2730) & (postnumber <= 2770)) |
                ((postnumber >= 2830) & (postnumber <= 2830)) | ((postnumber >= 2840) & (postnumber <= 2850)) |
                ((postnumber >= 2860) & (postnumber <= 2861)) | ((postnumber >= 2864) & (postnumber <= 2864)) |
                ((postnumber >= 2870) & (postnumber <= 2870)) | ((postnumber >= 2880) & (postnumber <= 2880)) |
                ((postnumber >= 2890) & (postnumber <= 2985)) | ((postnumber >= 3520) & (postnumber <= 3520)) |
                ((postnumber >= 3522) & (postnumber <= 3522)) | ((postnumber >= 3528) & (postnumber <= 3528)))

    tin3Cond9 = (((postnumber >= 6001) & (postnumber <= 6059)) | ((postnumber >= 6062) & (postnumber <= 6064)) |
                ((postnumber >= 6067) & (postnumber <= 6067)) | ((postnumber >= 6087) & (postnumber <= 6087)) |
                ((postnumber >= 6091) & (postnumber <= 6091)) | ((postnumber >= 6094) & (postnumber <= 6096)) |
                ((postnumber >= 6099) & (postnumber <= 6099)) | ((postnumber >= 6101) & (postnumber <= 6110)) |
                ((postnumber >= 6144) & (postnumber <= 6144)) | ((postnumber >= 6151) & (postnumber <= 6153)) |
                ((postnumber >= 6166) & (postnumber <= 6166)) | ((postnumber >= 6183) & (postnumber <= 6190)) |
                ((postnumber >= 6201) & (postnumber <= 6201)) | ((postnumber >= 6212) & (postnumber <= 6212)) |
                ((postnumber >= 6217) & (postnumber <= 6217)) | ((postnumber >= 6238) & (postnumber <= 6249)) |
                ((postnumber >= 6259) & (postnumber <= 6699)) | ((postnumber >= 6701) & (postnumber <= 6701)) |
                ((postnumber >= 6706) & (postnumber <= 6708)) | ((postnumber >= 6713) & (postnumber <= 6716)) |
                ((postnumber >= 6719) & (postnumber <= 6721)) | ((postnumber >= 6731) & (postnumber <= 6731)) |
                ((postnumber >= 6741) & (postnumber <= 6741)) | ((postnumber >= 6751) & (postnumber <= 6761)) |
                ((postnumber >= 6771) & (postnumber <= 6782)) | ((postnumber >= 6784) & (postnumber <= 6785)) |
                ((postnumber >= 6791) & (postnumber <= 6792)) | ((postnumber >= 6796) & (postnumber <= 6796)) |
                ((postnumber >= 6799) & (postnumber <= 6799)) | ((postnumber >= 6801) & (postnumber <= 6812)) |
                ((postnumber >= 6818) & (postnumber <= 6821)) | ((postnumber >= 6825) & (postnumber <= 6825)) |
                ((postnumber >= 6828) & (postnumber <= 6828)) | ((postnumber >= 6841) & (postnumber <= 6841)) |
                ((postnumber >= 6846) & (postnumber <= 6846)) | ((postnumber >= 6851) & (postnumber <= 6853)) |
                ((postnumber >= 6855) & (postnumber <= 6855)) | ((postnumber >= 6857) & (postnumber <= 6861)) |
                ((postnumber >= 6866) & (postnumber <= 6866)) | ((postnumber >= 6870) & (postnumber <= 6870)) |
                ((postnumber >= 6873) & (postnumber <= 6875)) | ((postnumber >= 6882) & (postnumber <= 6882)) |
                ((postnumber >= 6886) & (postnumber <= 6886)) | ((postnumber >= 6889) & (postnumber <= 6891)) |
                ((postnumber >= 6898) & (postnumber <= 6898)) | ((postnumber >= 6901) & (postnumber <= 6912)) |
                ((postnumber >= 6916) & (postnumber <= 6916)) | ((postnumber >= 6918) & (postnumber <= 6918)) |
                ((postnumber >= 6921) & (postnumber <= 6921)) | ((postnumber >= 6926) & (postnumber <= 6927)) |
                ((postnumber >= 6929) & (postnumber <= 6940)) | ((postnumber >= 6942) & (postnumber <= 6942)) |
                ((postnumber >= 6946) & (postnumber <= 6946)) | ((postnumber >= 6949) & (postnumber <= 6951)) |
                ((postnumber >= 6962) & (postnumber <= 6962)) | ((postnumber >= 6966) & (postnumber <= 6966)) |
                ((postnumber >= 6969) & (postnumber <= 6971)) | ((postnumber >= 6975) & (postnumber <= 6975)) |
                ((postnumber >= 6988) & (postnumber <= 6991)) | ((postnumber >= 7340) & (postnumber <= 7340)) |
                ((postnumber >= 7342) & (postnumber <= 7342)))

    tin3Cond10 = (((postnumber >= 7005) & (postnumber <= 7005)) | ((postnumber >= 7040) & (postnumber <= 7041)) |
                 ((postnumber >= 7044) & (postnumber <= 7046)) | ((postnumber >= 7052) & (postnumber <= 7056)) |
                 ((postnumber >= 7058) & (postnumber <= 7058)) | ((postnumber >= 7100) & (postnumber <= 7100)) |
                 ((postnumber >= 7105) & (postnumber <= 7114)) | ((postnumber >= 7120) & (postnumber <= 7120)) |
                 ((postnumber >= 7125) & (postnumber <= 7125)) | ((postnumber >= 7130) & (postnumber <= 7140)) |
                 ((postnumber >= 7150) & (postnumber <= 7150)) | ((postnumber >= 7160) & (postnumber <= 7160)) |
                 ((postnumber >= 7167) & (postnumber <= 7168)) | ((postnumber >= 7170) & (postnumber <= 7170)) |
                 ((postnumber >= 7177) & (postnumber <= 7194)) | ((postnumber >= 7500) & (postnumber <= 7500)) |
                 ((postnumber >= 7502) & (postnumber <= 7502)) | ((postnumber >= 7506) & (postnumber <= 7533)) |
                 ((postnumber >= 7541) & (postnumber <= 7981)) | ((postnumber >= 7985) & (postnumber <= 7994)))

    tin3Cond11 = (((postnumber >= 7982) & (postnumber <= 7982)) | ((postnumber >= 8000) & (postnumber <= 8409)) |
                  ((postnumber >= 8412) & (postnumber <= 8523)) | ((postnumber >= 8531) & (postnumber <= 8531)) |
                  ((postnumber >= 8535) & (postnumber <= 9000)))

    tin3Cond12 = (((postnumber >= 10) & (postnumber <= 153)) | ((postnumber >= 155) & (postnumber <= 187)) |
                  ((postnumber >= 191) & (postnumber <= 176)) | ((postnumber >= 280) & (postnumber <= 281)) |
                  ((postnumber >= 287) & (postnumber <= 372)) | ((postnumber >= 377) & (postnumber <= 377)) |
                  ((postnumber >= 379) & (postnumber <= 380)) | ((postnumber >= 382) & (postnumber <= 382)) |
                  ((postnumber >= 401) & (postnumber <= 560)) | ((postnumber >= 562) & (postnumber <= 575)) |
                  ((postnumber >= 667) & (postnumber <= 667)) | ((postnumber >= 701) & (postnumber <= 750)) |
                  ((postnumber >= 752) & (postnumber <= 752)) | ((postnumber >= 754) & (postnumber <= 755)) |
                  ((postnumber >= 759) & (postnumber <= 767)) | ((postnumber >= 770) & (postnumber <= 770)) |
                  ((postnumber >= 772) & (postnumber <= 772)) | ((postnumber >= 774) & (postnumber <= 775)) |
                  ((postnumber >= 778) & (postnumber <= 783)) | ((postnumber >= 785) & (postnumber <= 850)) |
                  ((postnumber >= 854) & (postnumber <= 854)) | ((postnumber >= 856) & (postnumber <= 857)) |
                  ((postnumber >= 861) & (postnumber <= 861)) | ((postnumber >= 863) & (postnumber <= 863)) |
                  ((postnumber >= 870) & (postnumber <= 891)))

    tin3Cond13 = (((postnumber >= 154) & (postnumber <= 154)) | ((postnumber >= 188) & (postnumber <= 190)) |
                 ((postnumber >= 561) & (postnumber <= 561)) | ((postnumber >= 576) & (postnumber <= 666)) |
                 ((postnumber >= 668) & (postnumber <= 694)) | ((postnumber >= 777) & (postnumber <= 777)) |
                 ((postnumber >= 901) & (postnumber <= 1295)))

    tin3Cond14 = (((postnumber >= 4001) & (postnumber <= 4394)) | ((postnumber >= 4440) & (postnumber <= 4463)) |
                 ((postnumber >= 5501) & (postnumber <= 5539)) | ((postnumber >= 5542) & (postnumber <= 5545)) |
                 ((postnumber >= 5547) & (postnumber <= 5549)) | ((postnumber >= 5560) & (postnumber <= 5574)) |
                 ((postnumber >= 5576) & (postnumber <= 5576)) | ((postnumber >= 5580) & (postnumber <= 5585)) |
                 ((postnumber >= 5590) & (postnumber <= 5593)) | ((postnumber >= 5596) & (postnumber <= 5596)))

    tin3Cond15 = (((postnumber >= 5743) & (postnumber <= 5747)) | ((postnumber >= 5962) & (postnumber <= 5962)) |
                 ((postnumber >= 6060) & (postnumber <= 6060)) | ((postnumber >= 6065) & (postnumber <= 6065)) |
                 ((postnumber >= 6069) & (postnumber <= 6085)) | ((postnumber >= 6089) & (postnumber <= 6090)) |
                 ((postnumber >= 6092) & (postnumber <= 6092)) | ((postnumber >= 6098) & (postnumber <= 6098)) |
                 ((postnumber >= 6100) & (postnumber <= 6100)) | ((postnumber >= 6120) & (postnumber <= 6143)) |
                 ((postnumber >= 6146) & (postnumber <= 6150)) | ((postnumber >= 6160) & (postnumber <= 6165)) |
                 ((postnumber >= 6170) & (postnumber <= 6174)) | ((postnumber >= 6196) & (postnumber <= 6200)) |
                 ((postnumber >= 6210) & (postnumber <= 6210)) | ((postnumber >= 6213) & (postnumber <= 6216)) |
                 ((postnumber >= 6218) & (postnumber <= 6230)) | ((postnumber >= 6250) & (postnumber <= 6250)) |
                 ((postnumber >= 6700) & (postnumber <= 6700)) | ((postnumber >= 6704) & (postnumber <= 6704)) |
                 ((postnumber >= 6710) & (postnumber <= 6711)) | ((postnumber >= 6717) & (postnumber <= 6718)) |
                 ((postnumber >= 6723) & (postnumber <= 6730)) | ((postnumber >= 6734) & (postnumber <= 6740)) |
                 ((postnumber >= 6750) & (postnumber <= 6750)) | ((postnumber >= 6763) & (postnumber <= 6770)) |
                 ((postnumber >= 6783) & (postnumber <= 6783)) | ((postnumber >= 6788) & (postnumber <= 6789)) |
                 ((postnumber >= 6793) & (postnumber <= 6795)) | ((postnumber >= 6797) & (postnumber <= 6798)) |
                 ((postnumber >= 6800) & (postnumber <= 6800)) | ((postnumber >= 6817) & (postnumber <= 6817)) |
                 ((postnumber >= 6823) & (postnumber <= 6823)) | ((postnumber >= 6826) & (postnumber <= 6827)) |
                 ((postnumber >= 6829) & (postnumber <= 6829)) | ((postnumber >= 6843) & (postnumber <= 6843)) |
                 ((postnumber >= 6847) & (postnumber <= 6848)) | ((postnumber >= 6854) & (postnumber <= 6854)) |
                 ((postnumber >= 6856) & (postnumber <= 6856)) | ((postnumber >= 6863) & (postnumber <= 6863)) |
                 ((postnumber >= 6868) & (postnumber <= 6869)) | ((postnumber >= 6871) & (postnumber <= 6872)) |
                 ((postnumber >= 6876) & (postnumber <= 6881)) | ((postnumber >= 6884) & (postnumber <= 6885)) |
                 ((postnumber >= 6887) & (postnumber <= 6888)) | ((postnumber >= 6893) & (postnumber <= 6896)) |
                 ((postnumber >= 6899) & (postnumber <= 6900)) | ((postnumber >= 6914) & (postnumber <= 6915)) |
                 ((postnumber >= 6917) & (postnumber <= 6917)) | ((postnumber >= 6919) & (postnumber <= 6919)) |
                 ((postnumber >= 6924) & (postnumber <= 6924)) | ((postnumber >= 6928) & (postnumber <= 6928)) |
                 ((postnumber >= 6941) & (postnumber <= 6941)) | ((postnumber >= 6944) & (postnumber <= 6944)) |
                 ((postnumber >= 6947) & (postnumber <= 6947)) | ((postnumber >= 6953) & (postnumber <= 6961)) |
                 ((postnumber >= 6963) & (postnumber <= 6964)) | ((postnumber >= 6967) & (postnumber <= 6968)) |
                 ((postnumber >= 6973) & (postnumber <= 6973)) | ((postnumber >= 6977) & (postnumber <= 6987)) |
                 ((postnumber >= 6993) & (postnumber <= 6996)))

    tin3Cond16 = (((postnumber >= 2500) & (postnumber <= 2500)) | ((postnumber >= 2510) & (postnumber <= 2542)) |
                 ((postnumber >= 2550) & (postnumber <= 2552)) | ((postnumber >= 2560) & (postnumber <= 2580)) |
                 ((postnumber >= 2584) & (postnumber <= 2584)) | ((postnumber >= 7002) & (postnumber <= 7004)) |
                 ((postnumber >= 7006) & (postnumber <= 7039)) | ((postnumber >= 7042) & (postnumber <= 7043)) |
                 ((postnumber >= 7047) & (postnumber <= 7051)) | ((postnumber >= 7057) & (postnumber <= 7057)) |
                 ((postnumber >= 7066) & (postnumber <= 7099)) | ((postnumber >= 7101) & (postnumber <= 7101)) |
                 ((postnumber >= 7119) & (postnumber <= 7119)) | ((postnumber >= 7121) & (postnumber <= 7121)) |
                 ((postnumber >= 7127) & (postnumber <= 7129)) | ((postnumber >= 7142) & (postnumber <= 7142)) |
                 ((postnumber >= 7152) & (postnumber <= 7159)) | ((postnumber >= 7165) & (postnumber <= 7166)) |
                 ((postnumber >= 7169) & (postnumber <= 7169)) | ((postnumber >= 7176) & (postnumber <= 7176)) |
                 ((postnumber >= 7200) & (postnumber <= 7338)) | ((postnumber >= 7341) & (postnumber <= 7341)) |
                 ((postnumber >= 7343) & (postnumber <= 7499)) | ((postnumber >= 7501) & (postnumber <= 7501)) |
                 ((postnumber >= 7505) & (postnumber <= 7505)) | ((postnumber >= 7540) & (postnumber <= 7540)))

    tin3Cond17 = (((postnumber >= 3650) & (postnumber <= 3656)) | ((postnumber >= 3660) & (postnumber <= 3999)))

    tin3Cond18 = (((postnumber >= 8410) & (postnumber <= 8410)) | ((postnumber >= 8530) & (postnumber <= 8530)) |
                  ((postnumber >= 8533) & (postnumber <= 8534)) | ((postnumber >= 9001) & (postnumber <= 9991)))

    tin3Cond19 = ((postnumber >= 3060) & (postnumber <= 3296))

    tin3Cond20 = (((postnumber >= 1401) & (postnumber <= 1403)) | ((postnumber >= 1409) & (postnumber <= 1409)) |
                  ((postnumber >= 1411) & (postnumber <= 1411)) | ((postnumber >= 1416) & (postnumber <= 1420)) |
                  ((postnumber >= 1431) & (postnumber <= 1432)) | ((postnumber >= 1441) & (postnumber <= 1444)) |
                  ((postnumber >= 1451) & (postnumber <= 1451)) | ((postnumber >= 1459) & (postnumber <= 1459)) |
                  ((postnumber >= 1471) & (postnumber <= 1471)) | ((postnumber >= 1483) & (postnumber <= 1487)) |
                  ((postnumber >= 1501) & (postnumber <= 1539)) | ((postnumber >= 1541) & (postnumber <= 1545)) |
                  ((postnumber >= 1556) & (postnumber <= 1892)) | ((postnumber >= 1950) & (postnumber <= 1950)))

    conditionList = [tin3Cond1, tin3Cond2, tin3Cond3, tin3Cond4, tin3Cond5, tin3Cond6, tin3Cond7, tin3Cond8,
                     tin3Cond9, tin3Cond10, tin3Cond11, tin3Cond12, tin3Cond13, tin3Cond14, tin3Cond15, tin3Cond16,
                     tin3Cond17, tin3Cond18, tin3Cond19, tin3Cond20]

    def conditioncheck(conditions):
        tin3 = ''
        for index, condition in enumerate(conditions):
            if condition is True:
                tin3 = index + 1
        return tin3

    tin3 = conditioncheck(conditionList)

    return tin3

def nomodul(modul):
    if (modul == "") is True:
        nomodul = ""
    else:
        nomodul = int(modul/100)

    return nomodul

def fylke(komkod):
    if (komkod == "") is True:
        fylke = ""
    else:
        fylke = int(komkod/100)

    return fylke

def valueDict():
    valueDict = {10: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    15: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    18: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    21: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 9, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    24: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 9, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    25: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 9, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    26: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    28: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 8, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    30: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    31: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    32: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    33: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    34: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    37: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    40: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    45: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    46: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    47: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    48: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    50: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    55: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    60: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    101: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    102: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    103: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    104: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    105: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    106: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    107: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    109: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    110: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    111: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    112: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    113: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    114: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    115: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    116: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    117: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    118: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    119: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    120: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    121: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    122: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    123: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    124: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    125: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    128: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    129: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 8, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    130: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    131: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    133: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    134: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    135: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    139: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    150: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    151: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    152: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    153: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    154: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 1, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    155: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 8, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    157: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    158: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 2, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    159: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    160: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    161: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    162: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 3, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    164: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    165: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    166: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    167: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 5, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    168: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    169: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    170: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    171: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    172: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    173: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    174: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    175: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    176: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 7, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    177: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 7, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    178: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    179: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 8, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    180: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 6, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    181: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 7, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    182: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 9, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    183: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 7, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    184: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 9, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    185: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    186: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    187: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    188: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    189: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    190: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    191: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    192: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    193: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    194: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    195: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    196: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    198: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    201: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    202: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    203: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    204: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 10, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    207: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    208: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    211: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    212: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    213: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    214: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    215: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    216: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    230: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    240: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 10, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    244: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    250: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    251: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    252: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    253: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    254: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    255: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    256: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 4, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    257: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    258: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    259: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 12, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    260: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    262: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    263: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    264: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    265: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    266: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    267: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    268: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    270: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    271: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    272: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 10, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    273: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 11, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    274: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    275: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    276: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    277: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    278: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    279: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    280: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    281: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    282: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    283: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    284: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    286: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    287: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 16, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    301: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    302: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    303: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    304: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    305: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    306: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    307: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    308: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    309: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    310: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    311: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    313: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    314: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    315: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    316: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    317: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    318: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    319: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    323: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    340: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    345: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    349: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    350: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 13, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    351: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 13, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    352: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 13, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    353: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    354: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    355: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    356: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 13, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    357: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    358: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    359: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    360: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    361: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    362: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    363: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    364: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    365: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    366: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    367: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    368: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 14, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    369: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    370: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 15, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    371: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    372: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    373: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    374: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    375: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    376: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    377: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    378: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    379: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    380: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    381: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    382: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    383: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 17, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    401: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    402: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    403: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    404: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    405: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    406: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    408: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    409: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    411: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    421: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    422: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    423: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    424: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    440: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    445: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    450: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    451: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    452: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    454: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    455: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    456: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    457: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    458: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    459: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    460: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 24, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    461: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 23, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    462: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 20, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    463: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 23, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    464: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 23, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    465: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 23, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    467: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    468: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    469: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 23, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    470: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    473: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    474: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    475: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    476: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    477: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    478: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    479: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    480: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    481: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    482: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    483: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 22, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    484: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    485: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    486: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    487: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    488: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    489: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    490: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    491: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    492: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    493: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    494: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    495: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    496: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    501: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    502: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    503: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    504: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    505: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    506: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    508: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    509: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    510: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    511: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    513: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    514: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    515: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    516: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    517: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    518: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 35, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    540: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    550: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 26, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    551: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 26, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    552: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    553: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    554: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 26, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    555: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    556: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    557: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 27, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    558: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    559: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    560: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 25, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    561: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    562: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    563: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    564: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    565: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    566: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    567: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    568: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    569: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    570: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    571: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    572: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    573: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    574: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 28, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    575: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    576: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    577: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    578: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    579: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    580: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    581: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    582: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    583: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    584: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    585: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    586: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 39, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    587: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 32, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    588: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    589: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    590: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    591: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    592: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    593: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    594: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 36, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    595: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 35, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    596: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 35, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    597: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 35, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    598: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 35, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    601: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    602: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    603: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    604: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    605: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    606: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    607: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    608: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 29, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    609: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    611: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    612: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    614: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    615: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    616: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    617: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    619: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    620: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    621: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    650: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    651: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    652: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    653: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    654: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    655: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    656: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 30, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    657: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    658: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 31, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    659: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    660: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    661: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    662: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    663: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    664: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    665: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    666: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 38, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    667: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    668: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    669: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    670: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    671: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    672: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    673: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    674: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    675: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    676: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    677: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    678: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    679: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    680: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    681: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    682: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    683: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    684: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    685: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    686: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    687: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    688: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    689: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    690: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 40, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    691: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    692: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    693: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    694: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    701: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    702: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    705: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    710: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    712: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    750: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    751: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    752: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    753: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    754: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    755: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    756: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    757: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    758: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    759: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    764: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    765: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    766: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    767: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    768: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    770: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    771: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    772: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    773: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    774: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    775: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    776: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    777: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    778: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    779: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    781: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    782: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    783: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    784: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    785: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    786: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    787: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    788: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    789: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    790: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    791: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 18, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    801: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    805: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    806: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    807: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    840: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    850: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    851: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    852: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    853: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    854: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    855: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    856: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    857: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    858: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    860: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    861: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    862: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    863: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    864: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 19, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    870: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    871: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    872: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    873: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    874: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    875: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    876: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    877: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    880: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    881: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    882: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    883: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    884: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    890: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    891: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 21, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    901: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    902: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    903: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    905: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    907: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    913: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    915: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    950: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    951: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    952: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    953: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    954: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    955: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    956: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    957: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    958: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    959: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    960: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    962: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    963: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    964: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    968: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    969: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    970: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    971: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    972: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    973: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    975: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    976: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    977: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 34, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    978: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    979: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    980: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    982: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    983: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    984: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    985: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    986: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    987: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    988: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1001: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1006: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1007: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1008: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1009: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1011: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1051: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1052: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1053: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1054: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1055: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1056: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1061: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1062: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1063: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1064: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1065: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1067: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1068: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1069: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1071: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1081: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1083: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1084: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 37, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1086: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1087: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1088: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1089: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 33, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1101: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1109: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1112: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1150: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1151: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1152: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1153: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1154: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1155: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1156: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1157: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1158: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1160: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1161: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1162: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1163: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1164: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1165: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1166: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1167: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1168: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1169: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1170: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1172: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1176: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1177: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1178: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1179: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1181: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1182: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1184: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1185: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 41, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1187: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1188: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1189: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1201: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1203: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1214: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1215: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1250: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1251: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1252: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1253: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1254: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1255: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1256: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1257: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1258: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1259: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1262: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1263: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 43, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1266: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1270: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1271: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1272: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1273: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1274: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1275: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1277: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1278: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1279: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1281: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1283: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1284: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1285: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1286: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1290: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1291: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1294: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1295: {'NO_KOMMUNEKOD': 301, 'hdi': 123, 'NO_MODUL1': 42, 'district': 1, 'NO_kreg': 391, 'New_Fylke': 3, 'New_kommune': 301},
                    1300: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1301: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1302: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1303: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1305: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1306: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1309: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1311: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1312: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1313: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1314: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1317: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1318: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1319: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1321: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1322: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1323: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1324: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1325: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1326: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1327: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1330: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1332: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1333: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1334: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1336: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1337: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1338: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1339: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1340: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1341: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1344: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1346: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1348: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1349: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1350: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1351: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1352: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1353: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1354: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 156, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1356: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1357: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1358: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 153, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1359: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 153, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1360: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 153, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1361: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 155, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1362: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 153, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1363: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1364: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1366: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1367: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1368: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1369: {'NO_KOMMUNEKOD': 219, 'hdi': 123, 'NO_MODUL1': 154, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3024},
                    1371: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1372: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1373: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1375: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1376: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1377: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1378: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1379: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1380: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1381: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1383: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1384: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1385: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1386: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1387: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1388: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1389: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1390: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1391: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1392: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1394: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1395: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1396: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1397: {'NO_KOMMUNEKOD': 220, 'hdi': 123, 'NO_MODUL1': 157, 'district': 2, 'NO_kreg': 292, 'New_Fylke': 30, 'New_kommune': 3025},
                    1400: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1401: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1402: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1403: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1404: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1405: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1406: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1407: {'NO_KOMMUNEKOD': 214, 'hdi': 122, 'NO_MODUL1': 104, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3021},
                    1408: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1409: {'NO_KOMMUNEKOD': 213, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1410: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1411: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1412: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1413: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1414: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1415: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1416: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1417: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1420: {'NO_KOMMUNEKOD': 217, 'hdi': 123, 'NO_MODUL1': 102, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3020},
                    1430: {'NO_KOMMUNEKOD': 214, 'hdi': 122, 'NO_MODUL1': 104, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3021},
                    1431: {'NO_KOMMUNEKOD': 214, 'hdi': 122, 'NO_MODUL1': 104, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3021},
                    1432: {'NO_KOMMUNEKOD': 214, 'hdi': 122, 'NO_MODUL1': 104, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3021},
                    1440: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1441: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1442: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1443: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1444: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1445: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1447: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1448: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 105, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1450: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1451: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1452: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1453: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1454: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1455: {'NO_KOMMUNEKOD': 215, 'hdi': 122, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3022},
                    1458: {'NO_KOMMUNEKOD': 216, 'hdi': 123, 'NO_MODUL1': 101, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3023},
                    1470: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1471: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1472: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1473: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1474: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1475: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1476: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1479: {'NO_KOMMUNEKOD': 230, 'hdi': 123, 'NO_MODUL1': 122, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3029},
                    1480: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1481: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1482: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1483: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1484: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1487: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1488: {'NO_KOMMUNEKOD': 233, 'hdi': 123, 'NO_MODUL1': 123, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3031},
                    1501: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1502: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1503: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1504: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1506: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1508: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1509: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1510: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1511: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1512: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1513: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1514: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1515: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1516: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1517: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1518: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1519: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1520: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1521: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1522: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1523: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1524: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1525: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1526: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1528: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1529: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1530: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1531: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1532: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1533: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1534: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1535: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1536: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1537: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1538: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1539: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1540: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1541: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1545: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1550: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1555: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1556: {'NO_KOMMUNEKOD': 211, 'hdi': 122, 'NO_MODUL1': 106, 'district': 2, 'NO_kreg': 291, 'New_Fylke': 30, 'New_kommune': 3019},
                    1560: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1570: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1580: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1581: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1590: {'NO_KOMMUNEKOD': 136, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1591: {'NO_KOMMUNEKOD': 137, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3018},
                    1592: {'NO_KOMMUNEKOD': 137, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3018},
                    1593: {'NO_KOMMUNEKOD': 137, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3018},
                    1596: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1597: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1598: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1599: {'NO_KOMMUNEKOD': 104, 'hdi': 114, 'NO_MODUL1': 108, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3002},
                    1600: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1601: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1602: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1604: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1605: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1606: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1607: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1608: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1609: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1610: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1612: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1613: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1614: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1615: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1616: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1617: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1618: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1619: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1620: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1621: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1624: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1625: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1626: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1628: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1629: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1630: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1632: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1633: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1634: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1636: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1637: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1638: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1639: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 111, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1640: {'NO_KOMMUNEKOD': 135, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3017},
                    1641: {'NO_KOMMUNEKOD': 135, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3017},
                    1642: {'NO_KOMMUNEKOD': 135, 'hdi': 114, 'NO_MODUL1': 109, 'district': 2, 'NO_kreg': 192, 'New_Fylke': 30, 'New_kommune': 3017},
                    1650: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1651: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1653: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1654: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1655: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1657: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1658: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1659: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1661: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1662: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1663: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1664: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1665: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1666: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1667: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 112, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1670: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1671: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1672: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1673: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1675: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1676: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1678: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1679: {'NO_KOMMUNEKOD': 106, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3004},
                    1680: {'NO_KOMMUNEKOD': 111, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3011},
                    1684: {'NO_KOMMUNEKOD': 111, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3011},
                    1690: {'NO_KOMMUNEKOD': 111, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3011},
                    1692: {'NO_KOMMUNEKOD': 111, 'hdi': 112, 'NO_MODUL1': 110, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3011},
                    1701: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1702: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1703: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1704: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1705: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1706: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1707: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1708: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1709: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1710: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1711: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1712: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1713: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1714: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 114, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1715: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 114, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1718: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 114, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1719: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 114, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1720: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 114, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1721: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1722: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1723: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1724: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1725: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1726: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1727: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 113, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1730: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1733: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1734: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1735: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1738: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1739: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1740: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1742: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1743: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1745: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1746: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1747: {'NO_KOMMUNEKOD': 105, 'hdi': 113, 'NO_MODUL1': 115, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3003},
                    1751: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1752: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1753: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1754: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1757: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1760: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1763: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1764: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1765: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1766: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1767: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1768: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1769: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1771: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1772: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1776: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1777: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1778: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1779: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1781: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1782: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1783: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1784: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1785: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1786: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1787: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1788: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1789: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1790: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1791: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1792: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1793: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1794: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1796: {'NO_KOMMUNEKOD': 101, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3001},
                    1798: {'NO_KOMMUNEKOD': 118, 'hdi': 111, 'NO_MODUL1': 116, 'district': 2, 'NO_kreg': 191, 'New_Fylke': 30, 'New_kommune': 3012},
                    1800: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1801: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1802: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1803: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1804: {'NO_KOMMUNEKOD': 123, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1805: {'NO_KOMMUNEKOD': 138, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1806: {'NO_KOMMUNEKOD': 127, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3015},
                    1807: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1808: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1809: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1811: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1812: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1813: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1814: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1815: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1816: {'NO_KOMMUNEKOD': 127, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3015},
                    1820: {'NO_KOMMUNEKOD': 123, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1823: {'NO_KOMMUNEKOD': 138, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1825: {'NO_KOMMUNEKOD': 138, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1827: {'NO_KOMMUNEKOD': 138, 'hdi': 121, 'NO_MODUL1': 107, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1830: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1831: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1832: {'NO_KOMMUNEKOD': 124, 'hdi': 121, 'NO_MODUL1': 118, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1850: {'NO_KOMMUNEKOD': 125, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1851: {'NO_KOMMUNEKOD': 125, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1859: {'NO_KOMMUNEKOD': 125, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1860: {'NO_KOMMUNEKOD': 122, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1861: {'NO_KOMMUNEKOD': 122, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1866: {'NO_KOMMUNEKOD': 122, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1870: {'NO_KOMMUNEKOD': 119, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3013},
                    1871: {'NO_KOMMUNEKOD': 119, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3013},
                    1875: {'NO_KOMMUNEKOD': 119, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3013},
                    1878: {'NO_KOMMUNEKOD': 125, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3014},
                    1890: {'NO_KOMMUNEKOD': 128, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3016},
                    1891: {'NO_KOMMUNEKOD': 128, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3016},
                    1892: {'NO_KOMMUNEKOD': 128, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 193, 'New_Fylke': 30, 'New_kommune': 3016},
                    1900: {'NO_KOMMUNEKOD': 227, 'hdi': 124, 'NO_MODUL1': 120, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1901: {'NO_KOMMUNEKOD': 227, 'hdi': 124, 'NO_MODUL1': 120, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1903: {'NO_KOMMUNEKOD': 227, 'hdi': 124, 'NO_MODUL1': 120, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1910: {'NO_KOMMUNEKOD': 227, 'hdi': 124, 'NO_MODUL1': 120, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1911: {'NO_KOMMUNEKOD': 229, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3028},
                    1912: {'NO_KOMMUNEKOD': 229, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3028},
                    1914: {'NO_KOMMUNEKOD': 229, 'hdi': 122, 'NO_MODUL1': 103, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3028},
                    1920: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1921: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1923: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1925: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1927: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    1929: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    1930: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1940: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1941: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1945: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1950: {'NO_KOMMUNEKOD': 121, 'hdi': 121, 'NO_MODUL1': 117, 'district': 2, 'NO_kreg': 194, 'New_Fylke': 30, 'New_kommune': 3026},
                    1954: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1960: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1963: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    1970: {'NO_KOMMUNEKOD': 221, 'hdi': 124, 'NO_MODUL1': 119, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3026},
                    2000: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2001: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2003: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2004: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2005: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2006: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 121, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2007: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2008: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 121, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2009: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 121, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2010: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2011: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2013: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2014: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 121, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2015: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2016: {'NO_KOMMUNEKOD': 226, 'hdi': 124, 'NO_MODUL1': 125, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2019: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2020: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2021: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2022: {'NO_KOMMUNEKOD': 234, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3032},
                    2024: {'NO_KOMMUNEKOD': 234, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3032},
                    2025: {'NO_KOMMUNEKOD': 228, 'hdi': 124, 'NO_MODUL1': 121, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3027},
                    2026: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2027: {'NO_KOMMUNEKOD': 231, 'hdi': 124, 'NO_MODUL1': 124, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3030},
                    2030: {'NO_KOMMUNEKOD': 238, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3036},
                    2031: {'NO_KOMMUNEKOD': 238, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3036},
                    2032: {'NO_KOMMUNEKOD': 238, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3036},
                    2033: {'NO_KOMMUNEKOD': 238, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3036},
                    2034: {'NO_KOMMUNEKOD': 238, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3036},
                    2040: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2041: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2050: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2051: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2052: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2053: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2055: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2056: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2058: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2060: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2061: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2063: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2066: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2067: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2069: {'NO_KOMMUNEKOD': 235, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3033},
                    2070: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2071: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2072: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2073: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 126, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2074: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2080: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2081: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2090: {'NO_KOMMUNEKOD': 239, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3037},
                    2091: {'NO_KOMMUNEKOD': 239, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3037},
                    2092: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2093: {'NO_KOMMUNEKOD': 237, 'hdi': 126, 'NO_MODUL1': 127, 'district': 2, 'NO_kreg': 294, 'New_Fylke': 30, 'New_kommune': 3035},
                    2100: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2101: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2110: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2114: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2116: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2120: {'NO_KOMMUNEKOD': 418, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3414},
                    2123: {'NO_KOMMUNEKOD': 418, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3414},
                    2130: {'NO_KOMMUNEKOD': 418, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3414},
                    2133: {'NO_KOMMUNEKOD': 418, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3414},
                    2134: {'NO_KOMMUNEKOD': 418, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3414},
                    2150: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2151: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2160: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2162: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2164: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2165: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2166: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2170: {'NO_KOMMUNEKOD': 236, 'hdi': 126, 'NO_MODUL1': 128, 'district': 2, 'NO_kreg': 293, 'New_Fylke': 30, 'New_kommune': 3034},
                    2201: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2202: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2203: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2204: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2205: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2206: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2208: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2209: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2210: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2211: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2212: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2213: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2214: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2216: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2217: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2218: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2219: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2220: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2223: {'NO_KOMMUNEKOD': 419, 'hdi': 127, 'NO_MODUL1': 129, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3415},
                    2224: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2225: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2226: {'NO_KOMMUNEKOD': 402, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3401},
                    2230: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2232: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2233: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2235: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2240: {'NO_KOMMUNEKOD': 420, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3416},
                    2256: {'NO_KOMMUNEKOD': 423, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3417},
                    2260: {'NO_KOMMUNEKOD': 423, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3417},
                    2264: {'NO_KOMMUNEKOD': 423, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3417},
                    2265: {'NO_KOMMUNEKOD': 423, 'hdi': 127, 'NO_MODUL1': 130, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3417},
                    2266: {'NO_KOMMUNEKOD': 425, 'hdi': 132, 'NO_MODUL1': 131, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3418},
                    2270: {'NO_KOMMUNEKOD': 425, 'hdi': 132, 'NO_MODUL1': 131, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3418},
                    2271: {'NO_KOMMUNEKOD': 425, 'hdi': 132, 'NO_MODUL1': 131, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3418},
                    2280: {'NO_KOMMUNEKOD': 425, 'hdi': 132, 'NO_MODUL1': 131, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3418},
                    2283: {'NO_KOMMUNEKOD': 425, 'hdi': 132, 'NO_MODUL1': 131, 'district': 2, 'NO_kreg': 491, 'New_Fylke': 34, 'New_kommune': 3418},
                    2301: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2302: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2303: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2304: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2305: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2306: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2307: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2308: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2312: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2315: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2316: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2317: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2318: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2319: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2320: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2321: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2322: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 136, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2323: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 136, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2324: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 136, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2325: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2326: {'NO_KOMMUNEKOD': 403, 'hdi': 131, 'NO_MODUL1': 134, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3403},
                    2330: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2332: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2334: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2335: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2337: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2338: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2340: {'NO_KOMMUNEKOD': 415, 'hdi': 131, 'NO_MODUL1': 136, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3412},
                    2344: {'NO_KOMMUNEKOD': 417, 'hdi': 131, 'NO_MODUL1': 133, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3413},
                    2345: {'NO_KOMMUNEKOD': 415, 'hdi': 131, 'NO_MODUL1': 136, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3412},
                    2350: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2353: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2355: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2360: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2364: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2365: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2372: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2380: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2381: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2382: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2383: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2386: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2388: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2390: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2391: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2401: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2402: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2403: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2404: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2405: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2406: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2407: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2408: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2409: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2410: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2411: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2412: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2414: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2415: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2416: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2418: {'NO_KOMMUNEKOD': 427, 'hdi': 133, 'NO_MODUL1': 137, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3420},
                    2420: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2421: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2422: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2423: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2425: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2427: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2428: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2429: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2430: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2432: {'NO_KOMMUNEKOD': 428, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3421},
                    2435: {'NO_KOMMUNEKOD': 426, 'hdi': 132, 'NO_MODUL1': 132, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3419},
                    2436: {'NO_KOMMUNEKOD': 426, 'hdi': 132, 'NO_MODUL1': 132, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3419},
                    2437: {'NO_KOMMUNEKOD': 426, 'hdi': 132, 'NO_MODUL1': 132, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3419},
                    2438: {'NO_KOMMUNEKOD': 426, 'hdi': 132, 'NO_MODUL1': 132, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3419},
                    2440: {'NO_KOMMUNEKOD': 434, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3425},
                    2443: {'NO_KOMMUNEKOD': 434, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3425},
                    2446: {'NO_KOMMUNEKOD': 434, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3425},
                    2448: {'NO_KOMMUNEKOD': 434, 'hdi': 133, 'NO_MODUL1': 139, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3425},
                    2450: {'NO_KOMMUNEKOD': 429, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3422},
                    2451: {'NO_KOMMUNEKOD': 429, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3422},
                    2460: {'NO_KOMMUNEKOD': 429, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3422},
                    2476: {'NO_KOMMUNEKOD': 430, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3423},
                    2477: {'NO_KOMMUNEKOD': 430, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3423},
                    2478: {'NO_KOMMUNEKOD': 432, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3424},
                    2480: {'NO_KOMMUNEKOD': 430, 'hdi': 133, 'NO_MODUL1': 138, 'district': 2, 'NO_kreg': 493, 'New_Fylke': 34, 'New_kommune': 3423},
                    2482: {'NO_KOMMUNEKOD': 432, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3424},
                    2485: {'NO_KOMMUNEKOD': 432, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3424},
                    2486: {'NO_KOMMUNEKOD': 432, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3424},
                    2487: {'NO_KOMMUNEKOD': 432, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3424},
                    2500: {'NO_KOMMUNEKOD': 437, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3427},
                    2501: {'NO_KOMMUNEKOD': 437, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3427},
                    2510: {'NO_KOMMUNEKOD': 437, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3427},
                    2512: {'NO_KOMMUNEKOD': 437, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3427},
                    2540: {'NO_KOMMUNEKOD': 436, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3426},
                    2542: {'NO_KOMMUNEKOD': 436, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3426},
                    2544: {'NO_KOMMUNEKOD': 436, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3426},
                    2550: {'NO_KOMMUNEKOD': 441, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3430},
                    2552: {'NO_KOMMUNEKOD': 441, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3430},
                    2555: {'NO_KOMMUNEKOD': 441, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3430},
                    2560: {'NO_KOMMUNEKOD': 438, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3428},
                    2580: {'NO_KOMMUNEKOD': 439, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3429},
                    2582: {'NO_KOMMUNEKOD': 439, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3429},
                    2584: {'NO_KOMMUNEKOD': 439, 'hdi': 134, 'NO_MODUL1': 140, 'district': 2, 'NO_kreg': 494, 'New_Fylke': 34, 'New_kommune': 3429},
                    2601: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2602: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2603: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2604: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2605: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2606: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2607: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2608: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2609: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2610: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2611: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2612: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2613: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2614: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2615: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2616: {'NO_KOMMUNEKOD': 412, 'hdi': 131, 'NO_MODUL1': 135, 'district': 2, 'NO_kreg': 492, 'New_Fylke': 34, 'New_kommune': 3411},
                    2617: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2618: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2619: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2624: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2625: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2626: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2629: {'NO_KOMMUNEKOD': 501, 'hdi': 141, 'NO_MODUL1': 146, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3405},
                    2630: {'NO_KOMMUNEKOD': 520, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3439},
                    2631: {'NO_KOMMUNEKOD': 520, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3439},
                    2632: {'NO_KOMMUNEKOD': 520, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3439},
                    2633: {'NO_KOMMUNEKOD': 520, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3439},
                    2634: {'NO_KOMMUNEKOD': 520, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3439},
                    2635: {'NO_KOMMUNEKOD': 521, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3440},
                    2636: {'NO_KOMMUNEKOD': 521, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3440},
                    2637: {'NO_KOMMUNEKOD': 521, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3440},
                    2639: {'NO_KOMMUNEKOD': 516, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3436},
                    2640: {'NO_KOMMUNEKOD': 516, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3436},
                    2642: {'NO_KOMMUNEKOD': 516, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3436},
                    2643: {'NO_KOMMUNEKOD': 516, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3436},
                    2646: {'NO_KOMMUNEKOD': 519, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3438},
                    2647: {'NO_KOMMUNEKOD': 519, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3438},
                    2648: {'NO_KOMMUNEKOD': 519, 'hdi': 142, 'NO_MODUL1': 143, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3438},
                    2649: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2651: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2652: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2653: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2656: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2657: {'NO_KOMMUNEKOD': 522, 'hdi': 141, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 591, 'New_Fylke': 34, 'New_kommune': 3441},
                    2658: {'NO_KOMMUNEKOD': 519, 'hdi': 142, 'NO_MODUL1': 145, 'district': 2, 'NO_kreg': 593, 'New_Fylke': 34, 'New_kommune': 3438},
                    2659: {'NO_KOMMUNEKOD': 511, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3431},
                    2660: {'NO_KOMMUNEKOD': 511, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3431},
                    2661: {'NO_KOMMUNEKOD': 511, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3431},
                    2662: {'NO_KOMMUNEKOD': 511, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3431},
                    2663: {'NO_KOMMUNEKOD': 511, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3431},
                    2665: {'NO_KOMMUNEKOD': 512, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3432},
                    2666: {'NO_KOMMUNEKOD': 512, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3432},
                    2667: {'NO_KOMMUNEKOD': 512, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3432},
                    2668: {'NO_KOMMUNEKOD': 512, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3432},
                    2669: {'NO_KOMMUNEKOD': 512, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3432},
                    2670: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2672: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2673: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2674: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2675: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2676: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2677: {'NO_KOMMUNEKOD': 517, 'hdi': 143, 'NO_MODUL1': 142, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3437},
                    2680: {'NO_KOMMUNEKOD': 515, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3435},
                    2682: {'NO_KOMMUNEKOD': 515, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3435},
                    2683: {'NO_KOMMUNEKOD': 515, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3435},
                    2684: {'NO_KOMMUNEKOD': 515, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3435},
                    2685: {'NO_KOMMUNEKOD': 514, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3434},
                    2686: {'NO_KOMMUNEKOD': 514, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3434},
                    2687: {'NO_KOMMUNEKOD': 514, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3434},
                    2688: {'NO_KOMMUNEKOD': 514, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3434},
                    2690: {'NO_KOMMUNEKOD': 513, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3433},
                    2693: {'NO_KOMMUNEKOD': 513, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3433},
                    2694: {'NO_KOMMUNEKOD': 513, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3433},
                    2695: {'NO_KOMMUNEKOD': 513, 'hdi': 143, 'NO_MODUL1': 141, 'district': 2, 'NO_kreg': 594, 'New_Fylke': 34, 'New_kommune': 3433},
                    2711: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2712: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2713: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2714: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2715: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2716: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2717: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2720: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2730: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2740: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2742: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2743: {'NO_KOMMUNEKOD': 533, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3054},
                    2750: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2760: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2770: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    2801: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2802: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2803: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2804: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2805: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2807: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2808: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2809: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2810: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2811: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2815: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2816: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2817: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2818: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2819: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2821: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2822: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2825: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2827: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2830: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2831: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2832: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2836: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2837: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2838: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2839: {'NO_KOMMUNEKOD': 502, 'hdi': 151, 'NO_MODUL1': 148, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3407},
                    2840: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2843: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2846: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2847: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2848: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2849: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2850: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2851: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2853: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2854: {'NO_KOMMUNEKOD': 529, 'hdi': 151, 'NO_MODUL1': 149, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3443},
                    2857: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2858: {'NO_KOMMUNEKOD': 528, 'hdi': 151, 'NO_MODUL1': 150, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3442},
                    2860: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2861: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2862: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2864: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2866: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2867: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2870: {'NO_KOMMUNEKOD': 538, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3448},
                    2879: {'NO_KOMMUNEKOD': 536, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3447},
                    2880: {'NO_KOMMUNEKOD': 538, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3448},
                    2881: {'NO_KOMMUNEKOD': 538, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3448},
                    2882: {'NO_KOMMUNEKOD': 538, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 592, 'New_Fylke': 34, 'New_kommune': 3448},
                    2890: {'NO_KOMMUNEKOD': 541, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3450},
                    2893: {'NO_KOMMUNEKOD': 541, 'hdi': 152, 'NO_MODUL1': 147, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3450},
                    2900: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2901: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2907: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2910: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2917: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2918: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2920: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2923: {'NO_KOMMUNEKOD': 542, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3451},
                    2929: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    2930: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    2933: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    2936: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    2937: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    2939: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2940: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2943: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2950: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2952: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2953: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2954: {'NO_KOMMUNEKOD': 544, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3453},
                    2959: {'NO_KOMMUNEKOD': 543, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3452},
                    2960: {'NO_KOMMUNEKOD': 543, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3452},
                    2966: {'NO_KOMMUNEKOD': 543, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3452},
                    2967: {'NO_KOMMUNEKOD': 543, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3452},
                    2973: {'NO_KOMMUNEKOD': 545, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3454},
                    2975: {'NO_KOMMUNEKOD': 545, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3454},
                    2977: {'NO_KOMMUNEKOD': 545, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3454},
                    2985: {'NO_KOMMUNEKOD': 545, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3454},
                    3001: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3002: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3003: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3004: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3005: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3006: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3007: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3008: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3009: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3011: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3012: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3013: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3014: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3015: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3016: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3017: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3018: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3019: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3021: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3022: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3023: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 209, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3024: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 210, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3025: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3026: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3027: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3028: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3029: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3030: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3031: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3032: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3033: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3034: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3035: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3036: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3037: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3038: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3039: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3040: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3041: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3042: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3043: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3044: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3045: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3046: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3047: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3048: {'NO_KOMMUNEKOD': 602, 'hdi': 171, 'NO_MODUL1': 211, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3050: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3051: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3053: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3054: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3055: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3056: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3057: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3058: {'NO_KOMMUNEKOD': 625, 'hdi': 171, 'NO_MODUL1': 212, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3005},
                    3060: {'NO_KOMMUNEKOD': 711, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 30, 'New_kommune': 3005},
                    3061: {'NO_KOMMUNEKOD': 711, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 30, 'New_kommune': 3005},
                    3070: {'NO_KOMMUNEKOD': 713, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 38, 'New_kommune': 3802},
                    3071: {'NO_KOMMUNEKOD': 713, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 38, 'New_kommune': 3802},
                    3075: {'NO_KOMMUNEKOD': 711, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 30, 'New_kommune': 3005},
                    3077: {'NO_KOMMUNEKOD': 711, 'hdi': 172, 'NO_MODUL1': 208, 'district': 3, 'NO_kreg': 794, 'New_Fylke': 30, 'New_kommune': 3005},
                    3080: {'NO_KOMMUNEKOD': 702, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3081: {'NO_KOMMUNEKOD': 702, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3088: {'NO_KOMMUNEKOD': 702, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3089: {'NO_KOMMUNEKOD': 702, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3090: {'NO_KOMMUNEKOD': 714, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3092: {'NO_KOMMUNEKOD': 714, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3095: {'NO_KOMMUNEKOD': 714, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 792, 'New_Fylke': 38, 'New_kommune': 3802},
                    3100: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3101: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3103: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3104: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3105: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3106: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3107: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3108: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3109: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3110: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3111: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3112: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3113: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3114: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3115: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3116: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3117: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3118: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3120: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3121: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3122: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3123: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3124: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3125: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3126: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3127: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3128: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3131: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 217, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3132: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3133: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3135: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3140: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3142: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3143: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3144: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3145: {'NO_KOMMUNEKOD': 723, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3148: {'NO_KOMMUNEKOD': 723, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3150: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3151: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3152: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3153: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3154: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3157: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3158: {'NO_KOMMUNEKOD': 719, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3159: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3160: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3161: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3162: {'NO_KOMMUNEKOD': 719, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3163: {'NO_KOMMUNEKOD': 722, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3164: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3165: {'NO_KOMMUNEKOD': 723, 'hdi': 182, 'NO_MODUL1': 218, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3811},
                    3166: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3167: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3168: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3170: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3171: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3172: {'NO_KOMMUNEKOD': 704, 'hdi': 182, 'NO_MODUL1': 216, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3173: {'NO_KOMMUNEKOD': 720, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3174: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3175: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3176: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3177: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3178: {'NO_KOMMUNEKOD': 716, 'hdi': 181, 'NO_MODUL1': 214, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3803},
                    3179: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3180: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3181: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3182: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3183: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3184: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3185: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3186: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3187: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3188: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3189: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3191: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3192: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3193: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3194: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3195: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3196: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3199: {'NO_KOMMUNEKOD': 701, 'hdi': 181, 'NO_MODUL1': 215, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3801},
                    3201: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3202: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3203: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3204: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3205: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3206: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3207: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3208: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3209: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3210: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3211: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3212: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3213: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3214: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3215: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3216: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3217: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3218: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3219: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3220: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3221: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3222: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3223: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3224: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3225: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3226: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3227: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3228: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3229: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3230: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3231: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3232: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3233: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3234: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3235: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3236: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3237: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3238: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3239: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3241: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3242: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3243: {'NO_KOMMUNEKOD': 719, 'hdi': 182, 'NO_MODUL1': 220, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3244: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3245: {'NO_KOMMUNEKOD': 719, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 791, 'New_Fylke': 38, 'New_kommune': 3804},
                    3246: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3249: {'NO_KOMMUNEKOD': 706, 'hdi': 183, 'NO_MODUL1': 219, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3804},
                    3250: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3251: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3252: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3254: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3255: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3256: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3257: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3258: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3259: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3260: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3261: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3262: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3263: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3264: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3265: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3267: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3268: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3269: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3270: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3271: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3274: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3275: {'NO_KOMMUNEKOD': 728, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3276: {'NO_KOMMUNEKOD': 728, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3277: {'NO_KOMMUNEKOD': 728, 'hdi': 184, 'NO_MODUL1': 221, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3280: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3282: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 221, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3290: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3291: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3292: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3294: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3295: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3296: {'NO_KOMMUNEKOD': 709, 'hdi': 184, 'NO_MODUL1': 222, 'district': 3, 'NO_kreg': 793, 'New_Fylke': 38, 'New_kommune': 3805},
                    3300: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3301: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3302: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3303: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3320: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3321: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3322: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3330: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3331: {'NO_KOMMUNEKOD': 624, 'hdi': 173, 'NO_MODUL1': 213, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3048},
                    3340: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3341: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3350: {'NO_KOMMUNEKOD': 621, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3045},
                    3351: {'NO_KOMMUNEKOD': 621, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3045},
                    3355: {'NO_KOMMUNEKOD': 621, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3045},
                    3358: {'NO_KOMMUNEKOD': 621, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3045},
                    3359: {'NO_KOMMUNEKOD': 621, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3045},
                    3360: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3361: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3370: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3371: {'NO_KOMMUNEKOD': 623, 'hdi': 173, 'NO_MODUL1': 205, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3047},
                    3400: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3401: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3402: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3403: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3408: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3410: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3412: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3414: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3420: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3421: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3425: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3427: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3428: {'NO_KOMMUNEKOD': 626, 'hdi': 171, 'NO_MODUL1': 206, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3049},
                    3430: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3431: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3440: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3441: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3442: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3470: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3471: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3472: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3474: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3475: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3476: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3477: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3478: {'NO_KOMMUNEKOD': 627, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3480: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3481: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3482: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3483: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3484: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3490: {'NO_KOMMUNEKOD': 628, 'hdi': 171, 'NO_MODUL1': 207, 'district': 3, 'NO_kreg': 691, 'New_Fylke': 30, 'New_kommune': 3025},
                    3501: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3502: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3503: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3504: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3510: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3511: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3512: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3513: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3514: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3515: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3516: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3517: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3518: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3519: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3520: {'NO_KOMMUNEKOD': 532, 'hdi': 162, 'NO_MODUL1': 152, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3053},
                    3521: {'NO_KOMMUNEKOD': 532, 'hdi': 162, 'NO_MODUL1': 152, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 30, 'New_kommune': 3053},
                    3522: {'NO_KOMMUNEKOD': 534, 'hdi': 125, 'NO_MODUL1': 151, 'district': 2, 'NO_kreg': 595, 'New_Fylke': 34, 'New_kommune': 3446},
                    3524: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3525: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3526: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3528: {'NO_KOMMUNEKOD': 540, 'hdi': 153, 'NO_MODUL1': 144, 'district': 2, 'NO_kreg': 596, 'New_Fylke': 34, 'New_kommune': 3449},
                    3529: {'NO_KOMMUNEKOD': 612, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3038},
                    3530: {'NO_KOMMUNEKOD': 612, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3038},
                    3531: {'NO_KOMMUNEKOD': 612, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3038},
                    3533: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3534: {'NO_KOMMUNEKOD': 605, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3007},
                    3535: {'NO_KOMMUNEKOD': 622, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3046},
                    3536: {'NO_KOMMUNEKOD': 622, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3046},
                    3537: {'NO_KOMMUNEKOD': 622, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3046},
                    3538: {'NO_KOMMUNEKOD': 612, 'hdi': 161, 'NO_MODUL1': 201, 'district': 3, 'NO_kreg': 693, 'New_Fylke': 30, 'New_kommune': 3038},
                    3539: {'NO_KOMMUNEKOD': 615, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3039},
                    3540: {'NO_KOMMUNEKOD': 616, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3040},
                    3541: {'NO_KOMMUNEKOD': 616, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3040},
                    3544: {'NO_KOMMUNEKOD': 616, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3040},
                    3550: {'NO_KOMMUNEKOD': 617, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3041},
                    3551: {'NO_KOMMUNEKOD': 617, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3041},
                    3560: {'NO_KOMMUNEKOD': 618, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3042},
                    3561: {'NO_KOMMUNEKOD': 618, 'hdi': 163, 'NO_MODUL1': 202, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3042},
                    3570: {'NO_KOMMUNEKOD': 619, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3043},
                    3571: {'NO_KOMMUNEKOD': 619, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3043},
                    3576: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3577: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3579: {'NO_KOMMUNEKOD': 619, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3043},
                    3580: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3581: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3588: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3593: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3595: {'NO_KOMMUNEKOD': 620, 'hdi': 163, 'NO_MODUL1': 203, 'district': 3, 'NO_kreg': 694, 'New_Fylke': 30, 'New_kommune': 3044},
                    3601: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3602: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3603: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3604: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3605: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3608: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3610: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3611: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3612: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3613: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3614: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3615: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3616: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3617: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3618: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3619: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3620: {'NO_KOMMUNEKOD': 631, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3050},
                    3621: {'NO_KOMMUNEKOD': 631, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3050},
                    3622: {'NO_KOMMUNEKOD': 631, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3050},
                    3623: {'NO_KOMMUNEKOD': 631, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3050},
                    3624: {'NO_KOMMUNEKOD': 631, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3050},
                    3626: {'NO_KOMMUNEKOD': 632, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3051},
                    3627: {'NO_KOMMUNEKOD': 632, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3051},
                    3628: {'NO_KOMMUNEKOD': 632, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3051},
                    3629: {'NO_KOMMUNEKOD': 633, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3052},
                    3630: {'NO_KOMMUNEKOD': 633, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3052},
                    3631: {'NO_KOMMUNEKOD': 633, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3052},
                    3632: {'NO_KOMMUNEKOD': 633, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3052},
                    3646: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3647: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3648: {'NO_KOMMUNEKOD': 604, 'hdi': 174, 'NO_MODUL1': 204, 'district': 3, 'NO_kreg': 692, 'New_Fylke': 30, 'New_kommune': 3006},
                    3650: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3652: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3656: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3658: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3660: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3661: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3665: {'NO_KOMMUNEKOD': 827, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3819},
                    3666: {'NO_KOMMUNEKOD': 826, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 894, 'New_Fylke': 38, 'New_kommune': 3818},
                    3671: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3672: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3673: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3674: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3675: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3676: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3677: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3678: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3679: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3680: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3681: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3683: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3684: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3690: {'NO_KOMMUNEKOD': 827, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3819},
                    3691: {'NO_KOMMUNEKOD': 807, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3808},
                    3692: {'NO_KOMMUNEKOD': 827, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3819},
                    3697: {'NO_KOMMUNEKOD': 827, 'hdi': 195, 'NO_MODUL1': 227, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3819},
                    3700: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3701: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3702: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3703: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3704: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3705: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3707: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3710: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3711: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3712: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3713: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3714: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3715: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3716: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3717: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3718: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3719: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3720: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3721: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3722: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3723: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3724: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3725: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3726: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3727: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3728: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3729: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3730: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3731: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3732: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3733: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3734: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3735: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3736: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3737: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3738: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3739: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3740: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3741: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3742: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3743: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3744: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3746: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3747: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3807},
                    3748: {'NO_KOMMUNEKOD': 811, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3812},
                    3749: {'NO_KOMMUNEKOD': 811, 'hdi': 193, 'NO_MODUL1': 224, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3812},
                    3750: {'NO_KOMMUNEKOD': 817, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3815},
                    3753: {'NO_KOMMUNEKOD': 817, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3815},
                    3760: {'NO_KOMMUNEKOD': 817, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3815},
                    3766: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3770: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3772: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3780: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3781: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3783: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3788: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3790: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3791: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3792: {'NO_KOMMUNEKOD': 806, 'hdi': 193, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3807},
                    3793: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3794: {'NO_KOMMUNEKOD': 815, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3814},
                    3795: {'NO_KOMMUNEKOD': 817, 'hdi': 192, 'NO_MODUL1': 230, 'district': 3, 'NO_kreg': 893, 'New_Fylke': 38, 'New_kommune': 3815},
                    3800: {'NO_KOMMUNEKOD': 821, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3801: {'NO_KOMMUNEKOD': 821, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3805: {'NO_KOMMUNEKOD': 821, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3810: {'NO_KOMMUNEKOD': 822, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3812: {'NO_KOMMUNEKOD': 822, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3820: {'NO_KOMMUNEKOD': 822, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3825: {'NO_KOMMUNEKOD': 819, 'hdi': 193, 'NO_MODUL1': 225, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3816},
                    3830: {'NO_KOMMUNEKOD': 819, 'hdi': 193, 'NO_MODUL1': 225, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3816},
                    3831: {'NO_KOMMUNEKOD': 819, 'hdi': 193, 'NO_MODUL1': 225, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3816},
                    3832: {'NO_KOMMUNEKOD': 819, 'hdi': 193, 'NO_MODUL1': 225, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3816},
                    3833: {'NO_KOMMUNEKOD': 821, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3834: {'NO_KOMMUNEKOD': 822, 'hdi': 195, 'NO_MODUL1': 226, 'district': 3, 'NO_kreg': 892, 'New_Fylke': 38, 'New_kommune': 3817},
                    3835: {'NO_KOMMUNEKOD': 828, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3820},
                    3836: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3840: {'NO_KOMMUNEKOD': 828, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3820},
                    3841: {'NO_KOMMUNEKOD': 828, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3820},
                    3844: {'NO_KOMMUNEKOD': 828, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3820},
                    3848: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3849: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3850: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3852: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3853: {'NO_KOMMUNEKOD': 829, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3821},
                    3854: {'NO_KOMMUNEKOD': 830, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3822},
                    3855: {'NO_KOMMUNEKOD': 830, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3822},
                    3860: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3864: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3870: {'NO_KOMMUNEKOD': 831, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3823},
                    3880: {'NO_KOMMUNEKOD': 833, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3824},
                    3882: {'NO_KOMMUNEKOD': 833, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3824},
                    3883: {'NO_KOMMUNEKOD': 830, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3822},
                    3884: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3885: {'NO_KOMMUNEKOD': 831, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3823},
                    3886: {'NO_KOMMUNEKOD': 833, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3824},
                    3887: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3888: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3890: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3891: {'NO_KOMMUNEKOD': 833, 'hdi': 194, 'NO_MODUL1': 229, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3824},
                    3893: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3895: {'NO_KOMMUNEKOD': 834, 'hdi': 196, 'NO_MODUL1': 228, 'district': 3, 'NO_kreg': 895, 'New_Fylke': 38, 'New_kommune': 3825},
                    3900: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3901: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3902: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3903: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3904: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3905: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3906: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3910: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3911: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3912: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3913: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3914: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3915: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3916: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3917: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3918: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3919: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3920: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3921: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3922: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3924: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3925: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3928: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3929: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3930: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3931: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3933: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3936: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3937: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3939: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3940: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3941: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3942: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3943: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3944: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3945: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3946: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3947: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3948: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3949: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3950: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3960: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3962: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3965: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3966: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3967: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3970: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3991: {'NO_KOMMUNEKOD': 805, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3806},
                    3993: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3995: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    3999: {'NO_KOMMUNEKOD': 814, 'hdi': 191, 'NO_MODUL1': 223, 'district': 3, 'NO_kreg': 891, 'New_Fylke': 38, 'New_kommune': 3813},
                    4001: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4002: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4003: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4004: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4005: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4006: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4007: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4008: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4009: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4010: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4011: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4012: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4013: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 313, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4014: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 311, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4015: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 311, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4016: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 310, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4017: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 310, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4018: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4019: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4020: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4021: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4022: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4023: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4024: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4025: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4026: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4027: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4028: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4029: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4031: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4032: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4033: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4034: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4035: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 309, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4041: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4042: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4043: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4044: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4045: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4046: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4047: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4048: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4049: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4050: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4051: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4052: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4053: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4054: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4055: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4056: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4057: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4064: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4065: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4066: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4067: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4068: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4069: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4070: {'NO_KOMMUNEKOD': 1127, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1127},
                    4073: {'NO_KOMMUNEKOD': 1127, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1127},
                    4076: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4083: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4085: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4086: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 314, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4088: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4089: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4090: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4091: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4092: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4093: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4094: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4095: {'NO_KOMMUNEKOD': 1103, 'hdi': 315, 'NO_MODUL1': 308, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4096: {'NO_KOMMUNEKOD': 1127, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1127},
                    4097: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4098: {'NO_KOMMUNEKOD': 1124, 'hdi': 315, 'NO_MODUL1': 307, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1124},
                    4100: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4102: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4110: {'NO_KOMMUNEKOD': 1129, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4119: {'NO_KOMMUNEKOD': 1129, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4120: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4122: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4123: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4124: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4126: {'NO_KOMMUNEKOD': 1130, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1130},
                    4127: {'NO_KOMMUNEKOD': 1129, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4128: {'NO_KOMMUNEKOD': 1129, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4129: {'NO_KOMMUNEKOD': 1129, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4130: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4134: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4137: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4139: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4146: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4148: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4150: {'NO_KOMMUNEKOD': 1142, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4152: {'NO_KOMMUNEKOD': 1142, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4153: {'NO_KOMMUNEKOD': 1142, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4156: {'NO_KOMMUNEKOD': 1142, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4158: {'NO_KOMMUNEKOD': 1142, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4160: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4163: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4164: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4167: {'NO_KOMMUNEKOD': 1133, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1133},
                    4168: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4169: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4170: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4173: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4174: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4180: {'NO_KOMMUNEKOD': 1144, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1144},
                    4182: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4187: {'NO_KOMMUNEKOD': 1141, 'hdi': 315, 'NO_MODUL1': 315, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1103},
                    4198: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4200: {'NO_KOMMUNEKOD': 1135, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1135},
                    4201: {'NO_KOMMUNEKOD': 1135, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1135},
                    4208: {'NO_KOMMUNEKOD': 1135, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1135},
                    4230: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4233: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4234: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4235: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4237: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4239: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4240: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4244: {'NO_KOMMUNEKOD': 1134, 'hdi': 322, 'NO_MODUL1': 316, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1134},
                    4250: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4251: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4260: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4262: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4264: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4265: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4270: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4272: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4274: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4275: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4276: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4280: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4291: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4294: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4295: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4296: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4297: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4298: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4299: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    4301: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4302: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4303: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4304: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4305: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4306: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4307: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4308: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4309: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4310: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4311: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4312: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4313: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4314: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4315: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4316: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4317: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4318: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4319: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4321: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4322: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4323: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4324: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4325: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4326: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4327: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4328: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4329: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4330: {'NO_KOMMUNEKOD': 1122, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1122},
                    4332: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4333: {'NO_KOMMUNEKOD': 1122, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1122},
                    4335: {'NO_KOMMUNEKOD': 1122, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1122},
                    4339: {'NO_KOMMUNEKOD': 1122, 'hdi': 314, 'NO_MODUL1': 305, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1122},
                    4340: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4342: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4343: {'NO_KOMMUNEKOD': 1120, 'hdi': 313, 'NO_MODUL1': 303, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1120},
                    4344: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4345: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4347: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4349: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4352: {'NO_KOMMUNEKOD': 1120, 'hdi': 313, 'NO_MODUL1': 303, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1120},
                    4353: {'NO_KOMMUNEKOD': 1120, 'hdi': 313, 'NO_MODUL1': 303, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1120},
                    4354: {'NO_KOMMUNEKOD': 1120, 'hdi': 313, 'NO_MODUL1': 303, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1120},
                    4355: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4356: {'NO_KOMMUNEKOD': 1121, 'hdi': 313, 'NO_MODUL1': 304, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1121},
                    4358: {'NO_KOMMUNEKOD': 1120, 'hdi': 313, 'NO_MODUL1': 303, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1120},
                    4360: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4362: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4363: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4364: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4365: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4367: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4368: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4369: {'NO_KOMMUNEKOD': 1119, 'hdi': 313, 'NO_MODUL1': 302, 'district': 4, 'NO_kreg': 1194, 'New_Fylke': 11, 'New_kommune': 1119},
                    4370: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4371: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4372: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4373: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4374: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4375: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4376: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4379: {'NO_KOMMUNEKOD': 1101, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1101},
                    4380: {'NO_KOMMUNEKOD': 1111, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1111},
                    4381: {'NO_KOMMUNEKOD': 1111, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1111},
                    4387: {'NO_KOMMUNEKOD': 1114, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1114},
                    4389: {'NO_KOMMUNEKOD': 1114, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1114},
                    4391: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4392: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4394: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4395: {'NO_KOMMUNEKOD': 1102, 'hdi': 314, 'NO_MODUL1': 306, 'district': 4, 'NO_kreg': 1192, 'New_Fylke': 11, 'New_kommune': 1108},
                    4400: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4401: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4420: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4432: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4434: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4436: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4438: {'NO_KOMMUNEKOD': 1004, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4207},
                    4440: {'NO_KOMMUNEKOD': 1046, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4228},
                    4443: {'NO_KOMMUNEKOD': 1046, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4228},
                    4460: {'NO_KOMMUNEKOD': 1112, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1112},
                    4462: {'NO_KOMMUNEKOD': 1112, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1112},
                    4463: {'NO_KOMMUNEKOD': 1112, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1112},
                    4465: {'NO_KOMMUNEKOD': 1112, 'hdi': 312, 'NO_MODUL1': 301, 'district': 4, 'NO_kreg': 1191, 'New_Fylke': 11, 'New_kommune': 1112},
                    4473: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4480: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4484: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4485: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4490: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4491: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4492: {'NO_KOMMUNEKOD': 1037, 'hdi': 311, 'NO_MODUL1': 244, 'district': 3, 'NO_kreg': 1094, 'New_Fylke': 42, 'New_kommune': 4227},
                    4501: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4502: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4503: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4504: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4505: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4506: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4507: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4508: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4509: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4510: {'NO_KOMMUNEKOD': 1029, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4513: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4514: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4515: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4516: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4517: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4519: {'NO_KOMMUNEKOD': 1002, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4520: {'NO_KOMMUNEKOD': 1029, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4521: {'NO_KOMMUNEKOD': 1029, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4523: {'NO_KOMMUNEKOD': 1029, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4525: {'NO_KOMMUNEKOD': 1027, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4225},
                    4528: {'NO_KOMMUNEKOD': 1027, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4225},
                    4529: {'NO_KOMMUNEKOD': 1027, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4225},
                    4532: {'NO_KOMMUNEKOD': 1021, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4534: {'NO_KOMMUNEKOD': 1021, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4536: {'NO_KOMMUNEKOD': 1021, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4205},
                    4540: {'NO_KOMMUNEKOD': 1026, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4224},
                    4544: {'NO_KOMMUNEKOD': 1026, 'hdi': 223, 'NO_MODUL1': 242, 'district': 3, 'NO_kreg': 1092, 'New_Fylke': 42, 'New_kommune': 4224},
                    4550: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4551: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4557: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4558: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4560: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4563: {'NO_KOMMUNEKOD': 1003, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4206},
                    4575: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4576: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4577: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4579: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4580: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4586: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4588: {'NO_KOMMUNEKOD': 1032, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4225},
                    4590: {'NO_KOMMUNEKOD': 1034, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4226},
                    4595: {'NO_KOMMUNEKOD': 1034, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4226},
                    4596: {'NO_KOMMUNEKOD': 1034, 'hdi': 225, 'NO_MODUL1': 243, 'district': 3, 'NO_kreg': 1093, 'New_Fylke': 42, 'New_kommune': 4226},
                    4604: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4605: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4606: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4608: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4609: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4610: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4611: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4612: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4613: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4614: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4615: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4616: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4617: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4618: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4619: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4621: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4622: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4623: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4624: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4625: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4626: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4628: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4629: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4630: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4631: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4632: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4633: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4634: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4635: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4636: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 238, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4637: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4638: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4639: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4640: {'NO_KOMMUNEKOD': 1018, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4641: {'NO_KOMMUNEKOD': 1018, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4645: {'NO_KOMMUNEKOD': 1017, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4646: {'NO_KOMMUNEKOD': 1017, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4647: {'NO_KOMMUNEKOD': 1017, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4656: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4657: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4658: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4659: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4661: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4662: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4663: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4664: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4665: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4666: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4671: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4673: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4674: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4675: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4676: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4677: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4679: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4682: {'NO_KOMMUNEKOD': 1018, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4683: {'NO_KOMMUNEKOD': 1018, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4685: {'NO_KOMMUNEKOD': 1017, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4686: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4687: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4688: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4689: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4691: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4693: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4696: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4697: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 239, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4698: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4699: {'NO_KOMMUNEKOD': 1001, 'hdi': 222, 'NO_MODUL1': 237, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4204},
                    4700: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4701: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4702: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4705: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4715: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4720: {'NO_KOMMUNEKOD': 1014, 'hdi': 222, 'NO_MODUL1': 240, 'district': 3, 'NO_kreg': 1091, 'New_Fylke': 42, 'New_kommune': 4223},
                    4724: {'NO_KOMMUNEKOD': 935, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4218},
                    4730: {'NO_KOMMUNEKOD': 935, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4218},
                    4733: {'NO_KOMMUNEKOD': 937, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4219},
                    4734: {'NO_KOMMUNEKOD': 937, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4219},
                    4735: {'NO_KOMMUNEKOD': 937, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4219},
                    4737: {'NO_KOMMUNEKOD': 937, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4219},
                    4741: {'NO_KOMMUNEKOD': 938, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4220},
                    4742: {'NO_KOMMUNEKOD': 938, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4220},
                    4745: {'NO_KOMMUNEKOD': 938, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4220},
                    4747: {'NO_KOMMUNEKOD': 940, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4221},
                    4748: {'NO_KOMMUNEKOD': 940, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4221},
                    4754: {'NO_KOMMUNEKOD': 941, 'hdi': 224, 'NO_MODUL1': 241, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4222},
                    4755: {'NO_KOMMUNEKOD': 941, 'hdi': 224, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 994, 'New_Fylke': 42, 'New_kommune': 4222},
                    4760: {'NO_KOMMUNEKOD': 928, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4216},
                    4766: {'NO_KOMMUNEKOD': 928, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4216},
                    4768: {'NO_KOMMUNEKOD': 928, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4216},
                    4770: {'NO_KOMMUNEKOD': 926, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4215},
                    4780: {'NO_KOMMUNEKOD': 926, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4215},
                    4790: {'NO_KOMMUNEKOD': 926, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4215},
                    4791: {'NO_KOMMUNEKOD': 926, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4215},
                    4792: {'NO_KOMMUNEKOD': 926, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4215},
                    4795: {'NO_KOMMUNEKOD': 928, 'hdi': 221, 'NO_MODUL1': 236, 'district': 3, 'NO_kreg': 993, 'New_Fylke': 42, 'New_kommune': 4216},
                    4801: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4802: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4803: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4808: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4809: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4810: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4812: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4815: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4816: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4817: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4818: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4820: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4821: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4823: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4824: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4825: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4827: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4828: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4830: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4832: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4834: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4836: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4838: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4839: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4841: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4842: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4843: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4844: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4846: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4847: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4848: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4849: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4851: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4852: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4853: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4854: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4855: {'NO_KOMMUNEKOD': 919, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4214},
                    4856: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4857: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4858: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4859: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 234, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4863: {'NO_KOMMUNEKOD': 929, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4217},
                    4864: {'NO_KOMMUNEKOD': 929, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4217},
                    4865: {'NO_KOMMUNEKOD': 929, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4217},
                    4868: {'NO_KOMMUNEKOD': 929, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4217},
                    4869: {'NO_KOMMUNEKOD': 929, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4217},
                    4870: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4876: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4877: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4878: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4879: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4885: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4886: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4887: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4888: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4889: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4891: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4892: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4894: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4896: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4898: {'NO_KOMMUNEKOD': 904, 'hdi': 212, 'NO_MODUL1': 235, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4202},
                    4900: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4901: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4909: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4910: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4912: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4915: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4916: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4920: {'NO_KOMMUNEKOD': 906, 'hdi': 212, 'NO_MODUL1': 233, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4203},
                    4934: {'NO_KOMMUNEKOD': 914, 'hdi': 211, 'NO_MODUL1': 232, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4213},
                    4950: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    4951: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    4956: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    4971: {'NO_KOMMUNEKOD': 911, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4211},
                    4972: {'NO_KOMMUNEKOD': 911, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4211},
                    4973: {'NO_KOMMUNEKOD': 912, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4212},
                    4974: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    4980: {'NO_KOMMUNEKOD': 911, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4211},
                    4985: {'NO_KOMMUNEKOD': 912, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 992, 'New_Fylke': 42, 'New_kommune': 4212},
                    4990: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    4993: {'NO_KOMMUNEKOD': 911, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4211},
                    4994: {'NO_KOMMUNEKOD': 901, 'hdi': 211, 'NO_MODUL1': 231, 'district': 3, 'NO_kreg': 991, 'New_Fylke': 42, 'New_kommune': 4201},
                    5003: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5004: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 333, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5005: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5006: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 332, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5007: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5008: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 330, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5009: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5010: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 332, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5011: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 333, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5012: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 333, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5013: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 331, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5014: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 332, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5015: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 335, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5016: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5017: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 332, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5018: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 331, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5019: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5020: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5021: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5033: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5034: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5035: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5036: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5038: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5039: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5041: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 336, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5045: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5050: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5052: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5053: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5054: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5055: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5056: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5057: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5058: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5059: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5063: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 329, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5067: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5068: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5071: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5072: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5073: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5075: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5081: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5089: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5093: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5094: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5096: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5097: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5098: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5101: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5104: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5105: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5106: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5107: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5108: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5109: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5111: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5113: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5114: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5115: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5116: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5117: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5118: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5119: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5121: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5124: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5130: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5131: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5132: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5134: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5135: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5136: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5137: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5141: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5142: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5143: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5144: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5145: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5146: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5147: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5148: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5151: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5152: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5155: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5160: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5161: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5162: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5163: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5164: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5165: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5170: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5171: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5172: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5173: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5174: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5177: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5178: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5179: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5183: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5184: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5200: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5201: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5202: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5203: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5207: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5209: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5210: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5212: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5215: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5216: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5217: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5218: {'NO_KOMMUNEKOD': 1243, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5221: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5222: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5223: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5224: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5225: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5227: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5228: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5229: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5231: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5232: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5235: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5236: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5237: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5238: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5239: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5243: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5244: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 328, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5248: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5251: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5252: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5253: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5254: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5257: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5258: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5259: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 327, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5260: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5261: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5262: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5263: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5264: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5265: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5267: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 337, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5268: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5281: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5282: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5283: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5284: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5285: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5286: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5291: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5293: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5299: {'NO_KOMMUNEKOD': 1253, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4630},
                    5300: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5302: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5303: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5304: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5305: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5306: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5307: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5308: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5309: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5310: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5314: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5315: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5318: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5321: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5322: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5323: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5325: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5326: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5327: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5329: {'NO_KOMMUNEKOD': 1247, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4627},
                    5331: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5333: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5334: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5335: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5336: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5337: {'NO_KOMMUNEKOD': 1259, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5341: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5342: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5343: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5345: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5346: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5347: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5350: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5353: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5355: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5357: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5358: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5360: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5363: {'NO_KOMMUNEKOD': 1246, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5371: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5374: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5378: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5379: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5380: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5381: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5382: {'NO_KOMMUNEKOD': 1245, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4626},
                    5384: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5385: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5387: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5388: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5392: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5393: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5394: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5396: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5397: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5398: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5399: {'NO_KOMMUNEKOD': 1244, 'hdi': 331, 'NO_MODUL1': 326, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4625},
                    5401: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5402: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5403: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5404: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5406: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5407: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5408: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5409: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5410: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5411: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5412: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5413: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5414: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5415: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5416: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5417: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5418: {'NO_KOMMUNEKOD': 1222, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4615},
                    5419: {'NO_KOMMUNEKOD': 1222, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4615},
                    5420: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5423: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5427: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5428: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5430: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5437: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5440: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5443: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5444: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5445: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5447: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5449: {'NO_KOMMUNEKOD': 1219, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4613},
                    5450: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5451: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5452: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5453: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5454: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5455: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5457: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5458: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5459: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5460: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5462: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5463: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5464: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5470: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5472: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5473: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5474: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5475: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5476: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5480: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5484: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5486: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5497: {'NO_KOMMUNEKOD': 1221, 'hdi': 324, 'NO_MODUL1': 321, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4614},
                    5498: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5499: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5501: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5502: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5503: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5504: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5505: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5506: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5507: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5508: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5513: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5514: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5515: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5516: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5517: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5518: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5519: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5521: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5522: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5523: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5525: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5527: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5528: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5529: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5531: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5532: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5533: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5534: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5535: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5536: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5537: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5538: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5541: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5542: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5545: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5546: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5547: {'NO_KOMMUNEKOD': 1151, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1151},
                    5548: {'NO_KOMMUNEKOD': 1149, 'hdi': 321, 'NO_MODUL1': 318, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1149},
                    5549: {'NO_KOMMUNEKOD': 1106, 'hdi': 321, 'NO_MODUL1': 319, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1106},
                    5550: {'NO_KOMMUNEKOD': 1216, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4612},
                    5551: {'NO_KOMMUNEKOD': 1216, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4612},
                    5554: {'NO_KOMMUNEKOD': 1216, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4612},
                    5555: {'NO_KOMMUNEKOD': 1216, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4612},
                    5559: {'NO_KOMMUNEKOD': 1216, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4612},
                    5560: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5561: {'NO_KOMMUNEKOD': 1145, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1145},
                    5563: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5565: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5566: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5567: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5568: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5570: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5574: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5575: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5576: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5578: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5580: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5582: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5583: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5584: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5585: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5586: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5588: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5589: {'NO_KOMMUNEKOD': 1160, 'hdi': 321, 'NO_MODUL1': 317, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1160},
                    5590: {'NO_KOMMUNEKOD': 1211, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4611},
                    5593: {'NO_KOMMUNEKOD': 1211, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4611},
                    5594: {'NO_KOMMUNEKOD': 1211, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4611},
                    5595: {'NO_KOMMUNEKOD': 1146, 'hdi': 321, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1193, 'New_Fylke': 11, 'New_kommune': 1146},
                    5596: {'NO_KOMMUNEKOD': 1211, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4611},
                    5598: {'NO_KOMMUNEKOD': 1211, 'hdi': 323, 'NO_MODUL1': 320, 'district': 4, 'NO_kreg': 1292, 'New_Fylke': 46, 'New_kommune': 4611},
                    5600: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5601: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5602: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5604: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5605: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5610: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5612: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5614: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5620: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5626: {'NO_KOMMUNEKOD': 1227, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5627: {'NO_KOMMUNEKOD': 1227, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5628: {'NO_KOMMUNEKOD': 1227, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5629: {'NO_KOMMUNEKOD': 1227, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5630: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5632: {'NO_KOMMUNEKOD': 1238, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4622},
                    5635: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5636: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5637: {'NO_KOMMUNEKOD': 1224, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4617},
                    5640: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5641: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5642: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5643: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5645: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5646: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5647: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5649: {'NO_KOMMUNEKOD': 1241, 'hdi': 331, 'NO_MODUL1': 325, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4624},
                    5650: {'NO_KOMMUNEKOD': 1242, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4623},
                    5652: {'NO_KOMMUNEKOD': 1242, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4623},
                    5658: {'NO_KOMMUNEKOD': 1242, 'hdi': 331, 'NO_MODUL1': 324, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4623},
                    5680: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5681: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5683: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5685: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5687: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5690: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5693: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5694: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5695: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5696: {'NO_KOMMUNEKOD': 1223, 'hdi': 324, 'NO_MODUL1': 322, 'district': 4, 'NO_kreg': 1293, 'New_Fylke': 46, 'New_kommune': 4616},
                    5700: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5701: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5702: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5705: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5706: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5707: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5710: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5712: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5713: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5715: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5718: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5719: {'NO_KOMMUNEKOD': 1233, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4620},
                    5721: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5722: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5723: {'NO_KOMMUNEKOD': 1235, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5724: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5725: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5726: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5727: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5728: {'NO_KOMMUNEKOD': 1251, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4628},
                    5729: {'NO_KOMMUNEKOD': 1252, 'hdi': 331, 'NO_MODUL1': 339, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4629},
                    5730: {'NO_KOMMUNEKOD': 1233, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4620},
                    5731: {'NO_KOMMUNEKOD': 1233, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4620},
                    5733: {'NO_KOMMUNEKOD': 1234, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5734: {'NO_KOMMUNEKOD': 1233, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4620},
                    5736: {'NO_KOMMUNEKOD': 1234, 'hdi': 332, 'NO_MODUL1': 340, 'district': 4, 'NO_kreg': 1295, 'New_Fylke': 46, 'New_kommune': 4621},
                    5741: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5742: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5743: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5745: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5746: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5747: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5748: {'NO_KOMMUNEKOD': 1421, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4641},
                    5750: {'NO_KOMMUNEKOD': 1228, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5751: {'NO_KOMMUNEKOD': 1228, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5760: {'NO_KOMMUNEKOD': 1228, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5763: {'NO_KOMMUNEKOD': 1228, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5770: {'NO_KOMMUNEKOD': 1228, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5773: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5776: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5777: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5778: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5779: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5780: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5781: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5782: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5783: {'NO_KOMMUNEKOD': 1232, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4619},
                    5784: {'NO_KOMMUNEKOD': 1232, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4619},
                    5785: {'NO_KOMMUNEKOD': 1232, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4619},
                    5786: {'NO_KOMMUNEKOD': 1232, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4619},
                    5787: {'NO_KOMMUNEKOD': 1231, 'hdi': 325, 'NO_MODUL1': 323, 'district': 4, 'NO_kreg': 1294, 'New_Fylke': 46, 'New_kommune': 4618},
                    5802: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 333, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5803: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 333, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5804: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5805: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5806: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5807: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5808: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5809: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5811: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5812: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5815: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5816: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5817: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5821: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5824: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5825: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5826: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5829: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5835: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5836: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5837: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5838: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5845: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5847: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5848: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5849: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5851: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5852: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5853: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5854: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5857: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5858: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5859: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5861: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5862: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5863: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5868: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5869: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5872: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5873: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5876: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5877: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5878: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5881: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5884: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5886: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5888: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5889: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5892: {'NO_KOMMUNEKOD': 1201, 'hdi': 331, 'NO_MODUL1': 334, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4601},
                    5902: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5903: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5906: {'NO_KOMMUNEKOD': 1256, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5908: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5911: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5912: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5913: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5914: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5915: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5916: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5917: {'NO_KOMMUNEKOD': 1256, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5918: {'NO_KOMMUNEKOD': 1256, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5931: {'NO_KOMMUNEKOD': 1260, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5936: {'NO_KOMMUNEKOD': 1260, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5937: {'NO_KOMMUNEKOD': 1260, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5938: {'NO_KOMMUNEKOD': 1260, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5939: {'NO_KOMMUNEKOD': 1260, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5941: {'NO_KOMMUNEKOD': 1264, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4632},
                    5943: {'NO_KOMMUNEKOD': 1264, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4632},
                    5947: {'NO_KOMMUNEKOD': 1265, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4633},
                    5948: {'NO_KOMMUNEKOD': 1265, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4633},
                    5951: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5953: {'NO_KOMMUNEKOD': 1264, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4632},
                    5954: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5955: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5956: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5957: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5960: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5961: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5962: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    5966: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5967: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5970: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5977: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5978: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5979: {'NO_KOMMUNEKOD': 1411, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4635},
                    5981: {'NO_KOMMUNEKOD': 1266, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4634},
                    5983: {'NO_KOMMUNEKOD': 1266, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4634},
                    5984: {'NO_KOMMUNEKOD': 1266, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4634},
                    5986: {'NO_KOMMUNEKOD': 1266, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4634},
                    5987: {'NO_KOMMUNEKOD': 1266, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4634},
                    5991: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5993: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    5994: {'NO_KOMMUNEKOD': 1263, 'hdi': 333, 'NO_MODUL1': 338, 'district': 4, 'NO_kreg': 1291, 'New_Fylke': 46, 'New_kommune': 4631},
                    6001: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6002: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6003: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6004: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6005: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6006: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6007: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6008: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6009: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6010: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6011: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6012: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6013: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6014: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6015: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6016: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6017: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6018: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6019: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6020: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6021: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6022: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6023: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6024: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6025: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6026: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6028: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6030: {'NO_KOMMUNEKOD': 1531, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1531},
                    6035: {'NO_KOMMUNEKOD': 1531, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1531},
                    6036: {'NO_KOMMUNEKOD': 1531, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1531},
                    6037: {'NO_KOMMUNEKOD': 1531, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1531},
                    6039: {'NO_KOMMUNEKOD': 1531, 'hdi': 344, 'NO_MODUL1': 406, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1531},
                    6040: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6045: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6050: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6052: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6055: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6057: {'NO_KOMMUNEKOD': 1504, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6058: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6059: {'NO_KOMMUNEKOD': 1532, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1532},
                    6060: {'NO_KOMMUNEKOD': 1517, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1517},
                    6062: {'NO_KOMMUNEKOD': 1517, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1517},
                    6063: {'NO_KOMMUNEKOD': 1517, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1517},
                    6064: {'NO_KOMMUNEKOD': 1516, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1516},
                    6065: {'NO_KOMMUNEKOD': 1516, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1516},
                    6067: {'NO_KOMMUNEKOD': 1516, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1516},
                    6069: {'NO_KOMMUNEKOD': 1517, 'hdi': 341, 'NO_MODUL1': 403, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1517},
                    6070: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6076: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6080: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6082: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6083: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6084: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6085: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6087: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6089: {'NO_KOMMUNEKOD': 1514, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1514},
                    6090: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6092: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6094: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6095: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6096: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6098: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6099: {'NO_KOMMUNEKOD': 1515, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1515},
                    6100: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6101: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6102: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6103: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6105: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6110: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6120: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6133: {'NO_KOMMUNEKOD': 1519, 'hdi': 342, 'NO_MODUL1': 402, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1577},
                    6139: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6140: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6141: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6142: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6143: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6144: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6146: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6149: {'NO_KOMMUNEKOD': 1511, 'hdi': 341, 'NO_MODUL1': 401, 'district': 5, 'NO_kreg': 1594, 'New_Fylke': 15, 'New_kommune': 1511},
                    6150: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6151: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6153: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6160: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6165: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6166: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6170: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6174: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6183: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6184: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6190: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6196: {'NO_KOMMUNEKOD': 1520, 'hdi': 342, 'NO_MODUL1': 404, 'district': 5, 'NO_kreg': 1595, 'New_Fylke': 15, 'New_kommune': 1520},
                    6200: {'NO_KOMMUNEKOD': 1525, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1525},
                    6201: {'NO_KOMMUNEKOD': 1525, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1525},
                    6210: {'NO_KOMMUNEKOD': 1524, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6212: {'NO_KOMMUNEKOD': 1525, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1525},
                    6213: {'NO_KOMMUNEKOD': 1524, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6214: {'NO_KOMMUNEKOD': 1524, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6215: {'NO_KOMMUNEKOD': 1524, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6216: {'NO_KOMMUNEKOD': 1525, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1525},
                    6218: {'NO_KOMMUNEKOD': 1525, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1525},
                    6220: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6222: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6224: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6230: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6238: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6239: {'NO_KOMMUNEKOD': 1528, 'hdi': 343, 'NO_MODUL1': 405, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1528},
                    6240: {'NO_KOMMUNEKOD': 1523, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6249: {'NO_KOMMUNEKOD': 1523, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6250: {'NO_KOMMUNEKOD': 1526, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6259: {'NO_KOMMUNEKOD': 1526, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1578},
                    6260: {'NO_KOMMUNEKOD': 1529, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6263: {'NO_KOMMUNEKOD': 1529, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6264: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6265: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6270: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6272: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6280: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6281: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6282: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6283: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6285: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6290: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6292: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6293: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6294: {'NO_KOMMUNEKOD': 1534, 'hdi': 344, 'NO_MODUL1': 407, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6300: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6301: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6310: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6315: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6320: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6330: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6339: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6350: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6360: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6363: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6364: {'NO_KOMMUNEKOD': 1543, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6386: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6387: {'NO_KOMMUNEKOD': 1539, 'hdi': 412, 'NO_MODUL1': 409, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1539},
                    6390: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6391: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6392: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6393: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6394: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6395: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6396: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6397: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6398: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6399: {'NO_KOMMUNEKOD': 1535, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1535},
                    6401: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6402: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6403: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6404: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6405: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6407: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6408: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6409: {'NO_KOMMUNEKOD': 1547, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1547},
                    6411: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6412: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6413: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6414: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6415: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6416: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6418: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6419: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6421: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6422: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6425: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6429: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6430: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6433: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6440: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6443: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6444: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6445: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6447: {'NO_KOMMUNEKOD': 1548, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6450: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6453: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6454: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6455: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6456: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6457: {'NO_KOMMUNEKOD': 1502, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6460: {'NO_KOMMUNEKOD': 1543, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6462: {'NO_KOMMUNEKOD': 1543, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6470: {'NO_KOMMUNEKOD': 1543, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6472: {'NO_KOMMUNEKOD': 1543, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6475: {'NO_KOMMUNEKOD': 1545, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6476: {'NO_KOMMUNEKOD': 1545, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1506},
                    6480: {'NO_KOMMUNEKOD': 1547, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1547},
                    6481: {'NO_KOMMUNEKOD': 1547, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1547},
                    6483: {'NO_KOMMUNEKOD': 1546, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6484: {'NO_KOMMUNEKOD': 1546, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6486: {'NO_KOMMUNEKOD': 1546, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6487: {'NO_KOMMUNEKOD': 1546, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6488: {'NO_KOMMUNEKOD': 1546, 'hdi': 411, 'NO_MODUL1': 408, 'district': 5, 'NO_kreg': 1593, 'New_Fylke': 15, 'New_kommune': 1507},
                    6490: {'NO_KOMMUNEKOD': 1551, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6493: {'NO_KOMMUNEKOD': 1551, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6494: {'NO_KOMMUNEKOD': 1551, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6499: {'NO_KOMMUNEKOD': 1551, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1579},
                    6500: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6501: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6502: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6503: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6504: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6506: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6507: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6508: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6509: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6510: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6511: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6512: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6514: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6515: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6516: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6517: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6518: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6520: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6521: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6522: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6523: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6524: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6529: {'NO_KOMMUNEKOD': 1505, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1505},
                    6530: {'NO_KOMMUNEKOD': 1554, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1554},
                    6531: {'NO_KOMMUNEKOD': 1554, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1554},
                    6532: {'NO_KOMMUNEKOD': 1554, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1554},
                    6538: {'NO_KOMMUNEKOD': 1554, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1554},
                    6539: {'NO_KOMMUNEKOD': 1554, 'hdi': 414, 'NO_MODUL1': 414, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1554},
                    6570: {'NO_KOMMUNEKOD': 1573, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1573},
                    6571: {'NO_KOMMUNEKOD': 1573, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1573},
                    6590: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6600: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6601: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6610: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6611: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6612: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6613: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6620: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6622: {'NO_KOMMUNEKOD': 1563, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1563},
                    6628: {'NO_KOMMUNEKOD': 1560, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1560},
                    6629: {'NO_KOMMUNEKOD': 1560, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1560},
                    6630: {'NO_KOMMUNEKOD': 1560, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1560},
                    6631: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6633: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6636: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6637: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6638: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6639: {'NO_KOMMUNEKOD': 1557, 'hdi': 411, 'NO_MODUL1': 410, 'district': 5, 'NO_kreg': 1591, 'New_Fylke': 15, 'New_kommune': 1557},
                    6640: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6642: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6643: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6644: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6645: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6650: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6652: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6653: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6655: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6656: {'NO_KOMMUNEKOD': 1566, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 15, 'New_kommune': 1566},
                    6657: {'NO_KOMMUNEKOD': 1567, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5061},
                    6658: {'NO_KOMMUNEKOD': 1567, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5061},
                    6659: {'NO_KOMMUNEKOD': 1567, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5061},
                    6660: {'NO_KOMMUNEKOD': 1567, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 50, 'New_kommune': 5061},
                    6670: {'NO_KOMMUNEKOD': 1560, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1560},
                    6674: {'NO_KOMMUNEKOD': 1560, 'hdi': 413, 'NO_MODUL1': 411, 'district': 5, 'NO_kreg': 1596, 'New_Fylke': 15, 'New_kommune': 1560},
                    6680: {'NO_KOMMUNEKOD': 1571, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5011},
                    6683: {'NO_KOMMUNEKOD': 1571, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5011},
                    6686: {'NO_KOMMUNEKOD': 1571, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5011},
                    6687: {'NO_KOMMUNEKOD': 1571, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5011},
                    6688: {'NO_KOMMUNEKOD': 1571, 'hdi': 415, 'NO_MODUL1': 413, 'district': 5, 'NO_kreg': 1597, 'New_Fylke': 50, 'New_kommune': 5011},
                    6689: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6690: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6693: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6694: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6697: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6698: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6699: {'NO_KOMMUNEKOD': 1576, 'hdi': 414, 'NO_MODUL1': 415, 'district': 5, 'NO_kreg': 1592, 'New_Fylke': 15, 'New_kommune': 1576},
                    6700: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6701: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6704: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6707: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6708: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6710: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6711: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6713: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6714: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6715: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6716: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6717: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6718: {'NO_KOMMUNEKOD': 1439, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4602},
                    6719: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6721: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6723: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6726: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6727: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6729: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6730: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6731: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6734: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6737: {'NO_KOMMUNEKOD': 1438, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4648},
                    6740: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6741: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6750: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6751: {'NO_KOMMUNEKOD': 1441, 'hdi': 338, 'NO_MODUL1': 346, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6761: {'NO_KOMMUNEKOD': 1444, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 15, 'New_kommune': 1577},
                    6763: {'NO_KOMMUNEKOD': 1444, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 15, 'New_kommune': 1577},
                    6770: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6771: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6776: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6777: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6778: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6779: {'NO_KOMMUNEKOD': 1443, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4649},
                    6781: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6782: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6783: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6784: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6788: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6789: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6791: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6792: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6793: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6795: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6796: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6797: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6798: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6799: {'NO_KOMMUNEKOD': 1449, 'hdi': 338, 'NO_MODUL1': 348, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4651},
                    6800: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6801: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6806: {'NO_KOMMUNEKOD': 1433, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6807: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6812: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6813: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6817: {'NO_KOMMUNEKOD': 1433, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6818: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6819: {'NO_KOMMUNEKOD': 1432, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6821: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6823: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6826: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6827: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6828: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6829: {'NO_KOMMUNEKOD': 1445, 'hdi': 338, 'NO_MODUL1': 347, 'district': 4, 'NO_kreg': 1495, 'New_Fylke': 46, 'New_kommune': 4650},
                    6841: {'NO_KOMMUNEKOD': 1431, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6843: {'NO_KOMMUNEKOD': 1431, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6847: {'NO_KOMMUNEKOD': 1431, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6848: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6851: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6852: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6853: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6854: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6855: {'NO_KOMMUNEKOD': 1422, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4642},
                    6856: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6858: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6859: {'NO_KOMMUNEKOD': 1420, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6861: {'NO_KOMMUNEKOD': 1419, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6863: {'NO_KOMMUNEKOD': 1419, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4640},
                    6866: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6868: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6869: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6870: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6871: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6872: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6873: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6875: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6876: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6877: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6878: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6879: {'NO_KOMMUNEKOD': 1426, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4644},
                    6881: {'NO_KOMMUNEKOD': 1424, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4643},
                    6882: {'NO_KOMMUNEKOD': 1424, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4643},
                    6884: {'NO_KOMMUNEKOD': 1424, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4643},
                    6885: {'NO_KOMMUNEKOD': 1424, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4643},
                    6886: {'NO_KOMMUNEKOD': 1422, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4642},
                    6887: {'NO_KOMMUNEKOD': 1422, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4642},
                    6888: {'NO_KOMMUNEKOD': 1422, 'hdi': 335, 'NO_MODUL1': 341, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4642},
                    6891: {'NO_KOMMUNEKOD': 1417, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4639},
                    6893: {'NO_KOMMUNEKOD': 1417, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4639},
                    6894: {'NO_KOMMUNEKOD': 1417, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4639},
                    6895: {'NO_KOMMUNEKOD': 1417, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4639},
                    6896: {'NO_KOMMUNEKOD': 1417, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1493, 'New_Fylke': 46, 'New_kommune': 4639},
                    6898: {'NO_KOMMUNEKOD': 1418, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4640},
                    6899: {'NO_KOMMUNEKOD': 1418, 'hdi': 335, 'NO_MODUL1': 342, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4640},
                    6900: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6901: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6902: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6905: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6912: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6914: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6915: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6916: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6917: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6918: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6919: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6921: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6924: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6926: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6927: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6928: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6929: {'NO_KOMMUNEKOD': 1412, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4636},
                    6940: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6941: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6942: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6944: {'NO_KOMMUNEKOD': 1401, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1491, 'New_Fylke': 46, 'New_kommune': 4602},
                    6946: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6947: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6949: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6951: {'NO_KOMMUNEKOD': 1413, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4637},
                    6953: {'NO_KOMMUNEKOD': 1413, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4637},
                    6957: {'NO_KOMMUNEKOD': 1413, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4637},
                    6958: {'NO_KOMMUNEKOD': 1413, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4637},
                    6961: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6963: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6964: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6966: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6967: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6968: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6969: {'NO_KOMMUNEKOD': 1429, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4646},
                    6971: {'NO_KOMMUNEKOD': 1430, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6973: {'NO_KOMMUNEKOD': 1430, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6975: {'NO_KOMMUNEKOD': 1430, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6977: {'NO_KOMMUNEKOD': 1430, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6978: {'NO_KOMMUNEKOD': 1430, 'hdi': 336, 'NO_MODUL1': 344, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4647},
                    6980: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6982: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6983: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6984: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6985: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6986: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6987: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6988: {'NO_KOMMUNEKOD': 1428, 'hdi': 337, 'NO_MODUL1': 345, 'district': 4, 'NO_kreg': 1494, 'New_Fylke': 46, 'New_kommune': 4645},
                    6991: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6993: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6995: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    6996: {'NO_KOMMUNEKOD': 1416, 'hdi': 334, 'NO_MODUL1': 343, 'district': 4, 'NO_kreg': 1492, 'New_Fylke': 46, 'New_kommune': 4638},
                    7002: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7003: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7004: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7005: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7006: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7010: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7011: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7012: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7013: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7014: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7015: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7016: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7018: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7019: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7020: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7021: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7022: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7023: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7024: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7025: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7026: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7027: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7028: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7029: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7030: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7031: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7032: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7033: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7034: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7036: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7037: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7038: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7039: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7040: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 421, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7041: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 421, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7042: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7043: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 421, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7044: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7045: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7046: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7047: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7048: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7049: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 419, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7050: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7051: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7052: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7053: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7054: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7056: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7057: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7058: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7066: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7067: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7070: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7072: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7074: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7075: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7078: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7079: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7080: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7081: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7082: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7083: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7088: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7089: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7091: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7092: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7093: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7097: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7098: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7099: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 418, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7100: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7101: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7105: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7110: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7112: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7113: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7114: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7119: {'NO_KOMMUNEKOD': 1624, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5054},
                    7120: {'NO_KOMMUNEKOD': 1718, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5054},
                    7121: {'NO_KOMMUNEKOD': 1718, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5054},
                    7125: {'NO_KOMMUNEKOD': 1718, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5054},
                    7127: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7128: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7129: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7130: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7140: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7142: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7150: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7152: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7153: {'NO_KOMMUNEKOD': 1621, 'hdi': 427, 'NO_MODUL1': 432, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7156: {'NO_KOMMUNEKOD': 1622, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7159: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7160: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7165: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7166: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7167: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7168: {'NO_KOMMUNEKOD': 1627, 'hdi': 427, 'NO_MODUL1': 431, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5057},
                    7169: {'NO_KOMMUNEKOD': 1630, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7170: {'NO_KOMMUNEKOD': 1630, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7176: {'NO_KOMMUNEKOD': 1630, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7177: {'NO_KOMMUNEKOD': 1630, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7178: {'NO_KOMMUNEKOD': 1630, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7180: {'NO_KOMMUNEKOD': 1632, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7190: {'NO_KOMMUNEKOD': 1632, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7194: {'NO_KOMMUNEKOD': 1632, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5058},
                    7200: {'NO_KOMMUNEKOD': 1612, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5011},
                    7201: {'NO_KOMMUNEKOD': 1612, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5011},
                    7203: {'NO_KOMMUNEKOD': 1612, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5011},
                    7206: {'NO_KOMMUNEKOD': 1612, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5011},
                    7211: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7212: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7213: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7223: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7224: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7227: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7228: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7231: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7232: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7234: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7236: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7238: {'NO_KOMMUNEKOD': 1653, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5028},
                    7239: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7240: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7241: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7242: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7243: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7246: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7247: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7250: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7252: {'NO_KOMMUNEKOD': 1617, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5013},
                    7255: {'NO_KOMMUNEKOD': 1613, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5013},
                    7256: {'NO_KOMMUNEKOD': 1613, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5013},
                    7257: {'NO_KOMMUNEKOD': 1613, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7259: {'NO_KOMMUNEKOD': 1613, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7260: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7261: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7263: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7264: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7266: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7268: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7270: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7273: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7280: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7282: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7284: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7285: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7286: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7287: {'NO_KOMMUNEKOD': 1620, 'hdi': 423, 'NO_MODUL1': 416, 'district': 5, 'NO_kreg': 1692, 'New_Fylke': 50, 'New_kommune': 5014},
                    7288: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7289: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7290: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7291: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7295: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7298: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7300: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7301: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7310: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7315: {'NO_KOMMUNEKOD': 1622, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7316: {'NO_KOMMUNEKOD': 1622, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7318: {'NO_KOMMUNEKOD': 1622, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7319: {'NO_KOMMUNEKOD': 1622, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7320: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7321: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7327: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7329: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7330: {'NO_KOMMUNEKOD': 1638, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7331: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7332: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7333: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7334: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7335: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7336: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7338: {'NO_KOMMUNEKOD': 1636, 'hdi': 424, 'NO_MODUL1': 417, 'district': 5, 'NO_kreg': 1695, 'New_Fylke': 50, 'New_kommune': 5024},
                    7340: {'NO_KOMMUNEKOD': 1634, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5021},
                    7341: {'NO_KOMMUNEKOD': 1634, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5021},
                    7342: {'NO_KOMMUNEKOD': 1634, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5021},
                    7343: {'NO_KOMMUNEKOD': 1634, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5021},
                    7345: {'NO_KOMMUNEKOD': 1634, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5021},
                    7350: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7351: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7353: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7354: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7355: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7357: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7358: {'NO_KOMMUNEKOD': 1657, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5029},
                    7361: {'NO_KOMMUNEKOD': 1640, 'hdi': 422, 'NO_MODUL1': 425, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5025},
                    7370: {'NO_KOMMUNEKOD': 1640, 'hdi': 422, 'NO_MODUL1': 425, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5025},
                    7372: {'NO_KOMMUNEKOD': 1640, 'hdi': 422, 'NO_MODUL1': 425, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5025},
                    7374: {'NO_KOMMUNEKOD': 1640, 'hdi': 422, 'NO_MODUL1': 425, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5025},
                    7380: {'NO_KOMMUNEKOD': 1644, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5026},
                    7383: {'NO_KOMMUNEKOD': 1644, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5026},
                    7384: {'NO_KOMMUNEKOD': 1644, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1696, 'New_Fylke': 50, 'New_kommune': 5026},
                    7386: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7387: {'NO_KOMMUNEKOD': 1648, 'hdi': 422, 'NO_MODUL1': 424, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5027},
                    7391: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7392: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7393: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7397: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7398: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7399: {'NO_KOMMUNEKOD': 1635, 'hdi': 421, 'NO_MODUL1': 412, 'district': 5, 'NO_kreg': 1694, 'New_Fylke': 50, 'New_kommune': 5022},
                    7400: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7401: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7402: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7403: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7404: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7405: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7406: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7407: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7408: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7409: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7410: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7411: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7412: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7413: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7414: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7415: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7416: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7417: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7418: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7419: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7420: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7421: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7422: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7424: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7425: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7426: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7427: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7428: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7429: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7430: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7431: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7432: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7433: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7434: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7435: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7436: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7437: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7438: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7439: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7440: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7441: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7442: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7443: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7444: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7445: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7446: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7447: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7448: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7449: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7450: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7451: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7452: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7453: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7454: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7455: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7458: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7459: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7462: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7463: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7465: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7466: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7467: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7468: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7469: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7471: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7472: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7473: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7474: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7475: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7476: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7477: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7478: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7479: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7481: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7483: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7484: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7485: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7486: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7488: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7489: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7491: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7492: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7493: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7495: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7496: {'NO_KOMMUNEKOD': 1601, 'hdi': 425, 'NO_MODUL1': 422, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7500: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7501: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7502: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7503: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7506: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7509: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7510: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7517: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7519: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7520: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7525: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7529: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7530: {'NO_KOMMUNEKOD': 1711, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5034},
                    7531: {'NO_KOMMUNEKOD': 1711, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5034},
                    7533: {'NO_KOMMUNEKOD': 1711, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5034},
                    7540: {'NO_KOMMUNEKOD': 1662, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7541: {'NO_KOMMUNEKOD': 1662, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7549: {'NO_KOMMUNEKOD': 1662, 'hdi': 425, 'NO_MODUL1': 423, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5001},
                    7550: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7551: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7560: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7562: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7563: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7566: {'NO_KOMMUNEKOD': 1663, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5031},
                    7570: {'NO_KOMMUNEKOD': 1714, 'hdi': 426, 'NO_MODUL1': 427, 'district': 5, 'NO_kreg': 1793, 'New_Fylke': 50, 'New_kommune': 5035},
                    7580: {'NO_KOMMUNEKOD': 1664, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5032},
                    7581: {'NO_KOMMUNEKOD': 1664, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5032},
                    7583: {'NO_KOMMUNEKOD': 1664, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5032},
                    7584: {'NO_KOMMUNEKOD': 1664, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5032},
                    7590: {'NO_KOMMUNEKOD': 1665, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5033},
                    7591: {'NO_KOMMUNEKOD': 1665, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5033},
                    7596: {'NO_KOMMUNEKOD': 1664, 'hdi': 425, 'NO_MODUL1': 426, 'district': 5, 'NO_kreg': 1691, 'New_Fylke': 50, 'New_kommune': 5032},
                    7600: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7601: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7603: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7604: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7606: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7619: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7620: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7622: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7623: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7624: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7629: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7630: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7631: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7632: {'NO_KOMMUNEKOD': 1719, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5037},
                    7633: {'NO_KOMMUNEKOD': 1717, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5036},
                    7634: {'NO_KOMMUNEKOD': 1717, 'hdi': 431, 'NO_MODUL1': 429, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5036},
                    7650: {'NO_KOMMUNEKOD': 1721, 'hdi': 431, 'NO_MODUL1': 428, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5038},
                    7651: {'NO_KOMMUNEKOD': 1721, 'hdi': 431, 'NO_MODUL1': 428, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5038},
                    7653: {'NO_KOMMUNEKOD': 1721, 'hdi': 431, 'NO_MODUL1': 428, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5038},
                    7657: {'NO_KOMMUNEKOD': 1721, 'hdi': 431, 'NO_MODUL1': 428, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5038},
                    7660: {'NO_KOMMUNEKOD': 1721, 'hdi': 431, 'NO_MODUL1': 428, 'district': 5, 'NO_kreg': 1794, 'New_Fylke': 50, 'New_kommune': 5038},
                    7670: {'NO_KOMMUNEKOD': 1756, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5053},
                    7671: {'NO_KOMMUNEKOD': 1756, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5053},
                    7672: {'NO_KOMMUNEKOD': 1756, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5053},
                    7690: {'NO_KOMMUNEKOD': 1756, 'hdi': 431, 'NO_MODUL1': 430, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5053},
                    7701: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7702: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7703: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7704: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7705: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7707: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7708: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7709: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7710: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7711: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7712: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7713: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7714: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7715: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7716: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7717: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7718: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7724: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7725: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7726: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7729: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7730: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7732: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7734: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7735: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7736: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7737: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7738: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7739: {'NO_KOMMUNEKOD': 1702, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7740: {'NO_KOMMUNEKOD': 1633, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5020},
                    7742: {'NO_KOMMUNEKOD': 1633, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5020},
                    7744: {'NO_KOMMUNEKOD': 1633, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5020},
                    7745: {'NO_KOMMUNEKOD': 1749, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5049},
                    7746: {'NO_KOMMUNEKOD': 1749, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5049},
                    7748: {'NO_KOMMUNEKOD': 1633, 'hdi': 427, 'NO_MODUL1': 433, 'district': 5, 'NO_kreg': 1693, 'New_Fylke': 50, 'New_kommune': 5020},
                    7750: {'NO_KOMMUNEKOD': 1725, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5007},
                    7751: {'NO_KOMMUNEKOD': 1725, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5007},
                    7760: {'NO_KOMMUNEKOD': 1736, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5041},
                    7761: {'NO_KOMMUNEKOD': 1736, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5041},
                    7770: {'NO_KOMMUNEKOD': 1749, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5049},
                    7771: {'NO_KOMMUNEKOD': 1749, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5049},
                    7777: {'NO_KOMMUNEKOD': 1725, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5007},
                    7790: {'NO_KOMMUNEKOD': 1724, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7791: {'NO_KOMMUNEKOD': 1724, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7796: {'NO_KOMMUNEKOD': 1724, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7797: {'NO_KOMMUNEKOD': 1724, 'hdi': 432, 'NO_MODUL1': 434, 'district': 5, 'NO_kreg': 1791, 'New_Fylke': 50, 'New_kommune': 5006},
                    7800: {'NO_KOMMUNEKOD': 1703, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7801: {'NO_KOMMUNEKOD': 1703, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7817: {'NO_KOMMUNEKOD': 1748, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7818: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7819: {'NO_KOMMUNEKOD': 1703, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7820: {'NO_KOMMUNEKOD': 1703, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7822: {'NO_KOMMUNEKOD': 1703, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7856: {'NO_KOMMUNEKOD': 1748, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5007},
                    7860: {'NO_KOMMUNEKOD': 1744, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5047},
                    7863: {'NO_KOMMUNEKOD': 1744, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5047},
                    7864: {'NO_KOMMUNEKOD': 1744, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5047},
                    7869: {'NO_KOMMUNEKOD': 1744, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5047},
                    7870: {'NO_KOMMUNEKOD': 1742, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5045},
                    7871: {'NO_KOMMUNEKOD': 1742, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5045},
                    7873: {'NO_KOMMUNEKOD': 1742, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5045},
                    7882: {'NO_KOMMUNEKOD': 1738, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5042},
                    7884: {'NO_KOMMUNEKOD': 1738, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5042},
                    7890: {'NO_KOMMUNEKOD': 1740, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5044},
                    7892: {'NO_KOMMUNEKOD': 1740, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5044},
                    7893: {'NO_KOMMUNEKOD': 1740, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5044},
                    7896: {'NO_KOMMUNEKOD': 1740, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5044},
                    7898: {'NO_KOMMUNEKOD': 1739, 'hdi': 434, 'NO_MODUL1': 435, 'district': 5, 'NO_kreg': 1795, 'New_Fylke': 50, 'New_kommune': 5043},
                    7900: {'NO_KOMMUNEKOD': 1750, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7901: {'NO_KOMMUNEKOD': 1750, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7940: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7944: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7950: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7960: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7970: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7971: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7973: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7976: {'NO_KOMMUNEKOD': 1743, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5046},
                    7977: {'NO_KOMMUNEKOD': 1743, 'hdi': 433, 'NO_MODUL1': 436, 'district': 5, 'NO_kreg': 1792, 'New_Fylke': 50, 'New_kommune': 5046},
                    7980: {'NO_KOMMUNEKOD': 1811, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1811},
                    7981: {'NO_KOMMUNEKOD': 1811, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1811},
                    7982: {'NO_KOMMUNEKOD': 1811, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1811},
                    7985: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7990: {'NO_KOMMUNEKOD': 1751, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5060},
                    7993: {'NO_KOMMUNEKOD': 1755, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5052},
                    7994: {'NO_KOMMUNEKOD': 1755, 'hdi': 435, 'NO_MODUL1': 437, 'district': 5, 'NO_kreg': 1796, 'New_Fylke': 50, 'New_kommune': 5052},
                    8000: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8001: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8002: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8003: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8004: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8005: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8006: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8007: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8008: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8009: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8010: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8011: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8012: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8013: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8014: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8015: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8016: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8019: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8020: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8021: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8022: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8023: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8026: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8027: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8028: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8029: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8030: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8031: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8037: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8038: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8041: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8047: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8048: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8049: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8050: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8056: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8058: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8063: {'NO_KOMMUNEKOD': 1857, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1857},
                    8064: {'NO_KOMMUNEKOD': 1856, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1856},
                    8071: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8084: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8089: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8091: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8092: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8093: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8094: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8095: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8096: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8097: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8098: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8100: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8102: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8103: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8108: {'NO_KOMMUNEKOD': 1804, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1804},
                    8110: {'NO_KOMMUNEKOD': 1839, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1839},
                    8114: {'NO_KOMMUNEKOD': 1839, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1839},
                    8118: {'NO_KOMMUNEKOD': 1839, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1839},
                    8120: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8128: {'NO_KOMMUNEKOD': 1839, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1839},
                    8130: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8135: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8136: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8138: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8140: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8145: {'NO_KOMMUNEKOD': 1838, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1838},
                    8146: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8149: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8150: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8151: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8157: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8158: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8159: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8160: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8161: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8168: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8170: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8178: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8181: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8182: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8184: {'NO_KOMMUNEKOD': 1837, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1837},
                    8185: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8186: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8187: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8188: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8189: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8190: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8193: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8195: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8196: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8197: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8198: {'NO_KOMMUNEKOD': 1836, 'hdi': 511, 'NO_MODUL1': 505, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1836},
                    8200: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8201: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8205: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8206: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8208: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8210: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8215: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8220: {'NO_KOMMUNEKOD': 1845, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1845},
                    8226: {'NO_KOMMUNEKOD': 1845, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1845},
                    8230: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8231: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8232: {'NO_KOMMUNEKOD': 1845, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1845},
                    8233: {'NO_KOMMUNEKOD': 1841, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1841},
                    8250: {'NO_KOMMUNEKOD': 1840, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1840},
                    8251: {'NO_KOMMUNEKOD': 1840, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1840},
                    8255: {'NO_KOMMUNEKOD': 1840, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1840},
                    8256: {'NO_KOMMUNEKOD': 1840, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1840},
                    8260: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8261: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8264: {'NO_KOMMUNEKOD': 1845, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1845},
                    8266: {'NO_KOMMUNEKOD': 1845, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1845},
                    8270: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1875},
                    8271: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1875},
                    8273: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1875},
                    8274: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1875},
                    8275: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1875},
                    8276: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8281: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8283: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8285: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8286: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8288: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8289: {'NO_KOMMUNEKOD': 1848, 'hdi': 511, 'NO_MODUL1': 506, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1848},
                    8290: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8294: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8297: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8298: {'NO_KOMMUNEKOD': 1849, 'hdi': 512, 'NO_MODUL1': 507, 'district': 6, 'NO_kreg': 1891, 'New_Fylke': 18, 'New_kommune': 1875},
                    8300: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8301: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8305: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8309: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8310: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8311: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8312: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8313: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8314: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8315: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8316: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8320: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8322: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8323: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8324: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8325: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8328: {'NO_KOMMUNEKOD': 1865, 'hdi': 513, 'NO_MODUL1': 510, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1865},
                    8340: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8352: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8360: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8370: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8372: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8373: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8376: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8377: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8378: {'NO_KOMMUNEKOD': 1860, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1860},
                    8380: {'NO_KOMMUNEKOD': 1859, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1859},
                    8382: {'NO_KOMMUNEKOD': 1859, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1859},
                    8384: {'NO_KOMMUNEKOD': 1859, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1859},
                    8387: {'NO_KOMMUNEKOD': 1859, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1859},
                    8388: {'NO_KOMMUNEKOD': 1859, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1859},
                    8390: {'NO_KOMMUNEKOD': 1874, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1874},
                    8392: {'NO_KOMMUNEKOD': 1874, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1874},
                    8393: {'NO_KOMMUNEKOD': 1874, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1874},
                    8398: {'NO_KOMMUNEKOD': 1874, 'hdi': 513, 'NO_MODUL1': 509, 'district': 6, 'NO_kreg': 1897, 'New_Fylke': 18, 'New_kommune': 1874},
                    8400: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8401: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8403: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8405: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8406: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8407: {'NO_KOMMUNEKOD': 1870, 'hdi': 522, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1870},
                    8408: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8409: {'NO_KOMMUNEKOD': 1911, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5411},
                    8410: {'NO_KOMMUNEKOD': 1851, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1851},
                    8412: {'NO_KOMMUNEKOD': 1851, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1851},
                    8413: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8414: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8426: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8428: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8430: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8432: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8438: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8439: {'NO_KOMMUNEKOD': 1868, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1868},
                    8440: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 512, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8445: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8447: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8450: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8455: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8459: {'NO_KOMMUNEKOD': 1866, 'hdi': 522, 'NO_MODUL1': 511, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1866},
                    8465: {'NO_KOMMUNEKOD': 1867, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1867},
                    8469: {'NO_KOMMUNEKOD': 1867, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1867},
                    8470: {'NO_KOMMUNEKOD': 1867, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1867},
                    8475: {'NO_KOMMUNEKOD': 1867, 'hdi': 522, 'NO_MODUL1': 513, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1867},
                    8480: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8481: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8483: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8484: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8485: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8488: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8489: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8493: {'NO_KOMMUNEKOD': 1871, 'hdi': 522, 'NO_MODUL1': 514, 'district': 6, 'NO_kreg': 1898, 'New_Fylke': 18, 'New_kommune': 1871},
                    8501: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8502: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8503: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8504: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8505: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8506: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8507: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8508: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8509: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8510: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8512: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8513: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8514: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8515: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8516: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8517: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8520: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8522: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8523: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8530: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8531: {'NO_KOMMUNEKOD': 1805, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8533: {'NO_KOMMUNEKOD': 1853, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1853},
                    8534: {'NO_KOMMUNEKOD': 1853, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1853},
                    8535: {'NO_KOMMUNEKOD': 1853, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1853},
                    8536: {'NO_KOMMUNEKOD': 1853, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1853},
                    8539: {'NO_KOMMUNEKOD': 1853, 'hdi': 521, 'NO_MODUL1': 516, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1853},
                    8540: {'NO_KOMMUNEKOD': 1854, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1854},
                    8543: {'NO_KOMMUNEKOD': 1854, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1854},
                    8545: {'NO_KOMMUNEKOD': 1854, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1854},
                    8546: {'NO_KOMMUNEKOD': 1854, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1854},
                    8550: {'NO_KOMMUNEKOD': 1851, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1851},
                    8551: {'NO_KOMMUNEKOD': 1851, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1851},
                    8581: {'NO_KOMMUNEKOD': 1851, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1851},
                    8590: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8591: {'NO_KOMMUNEKOD': 1850, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 18, 'New_kommune': 1805},
                    8601: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8602: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8603: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8604: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8607: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8608: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8610: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8613: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8614: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8615: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8616: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8617: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8618: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8622: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8624: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8626: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8630: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8638: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8640: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8641: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8642: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8643: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8646: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8647: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8648: {'NO_KOMMUNEKOD': 1832, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1832},
                    8650: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8651: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8654: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8655: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8656: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8657: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8658: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8661: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8663: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8664: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8665: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8672: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8680: {'NO_KOMMUNEKOD': 1825, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1825},
                    8681: {'NO_KOMMUNEKOD': 1825, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1825},
                    8686: {'NO_KOMMUNEKOD': 1824, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1824},
                    8690: {'NO_KOMMUNEKOD': 1826, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1826},
                    8691: {'NO_KOMMUNEKOD': 1826, 'hdi': 442, 'NO_MODUL1': 502, 'district': 6, 'NO_kreg': 1895, 'New_Fylke': 18, 'New_kommune': 1826},
                    8700: {'NO_KOMMUNEKOD': 1828, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1828},
                    8701: {'NO_KOMMUNEKOD': 1828, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1828},
                    8720: {'NO_KOMMUNEKOD': 1828, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1828},
                    8723: {'NO_KOMMUNEKOD': 1828, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1828},
                    8724: {'NO_KOMMUNEKOD': 1828, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1828},
                    8725: {'NO_KOMMUNEKOD': 1833, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1896, 'New_Fylke': 18, 'New_kommune': 1833},
                    8730: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8732: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8733: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8735: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8740: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8742: {'NO_KOMMUNEKOD': 1835, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1835},
                    8743: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8750: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8752: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8753: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8762: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8764: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8766: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8767: {'NO_KOMMUNEKOD': 1834, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1834},
                    8770: {'NO_KOMMUNEKOD': 1835, 'hdi': 444, 'NO_MODUL1': 504, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1835},
                    8800: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8801: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8802: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8803: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8805: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8813: {'NO_KOMMUNEKOD': 1827, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1827},
                    8820: {'NO_KOMMUNEKOD': 1827, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1827},
                    8827: {'NO_KOMMUNEKOD': 1827, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1827},
                    8830: {'NO_KOMMUNEKOD': 1827, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1827},
                    8842: {'NO_KOMMUNEKOD': 1818, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1818},
                    8844: {'NO_KOMMUNEKOD': 1818, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1818},
                    8850: {'NO_KOMMUNEKOD': 1818, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1818},
                    8851: {'NO_KOMMUNEKOD': 1818, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1818},
                    8852: {'NO_KOMMUNEKOD': 1818, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1818},
                    8854: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8860: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8865: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8870: {'NO_KOMMUNEKOD': 1816, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1816},
                    8880: {'NO_KOMMUNEKOD': 1820, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1820},
                    8890: {'NO_KOMMUNEKOD': 1822, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1822},
                    8891: {'NO_KOMMUNEKOD': 1822, 'hdi': 443, 'NO_MODUL1': 503, 'district': 6, 'NO_kreg': 1894, 'New_Fylke': 18, 'New_kommune': 1822},
                    8900: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8901: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8905: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8907: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8910: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8920: {'NO_KOMMUNEKOD': 1812, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1812},
                    8921: {'NO_KOMMUNEKOD': 1812, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1812},
                    8960: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8961: {'NO_KOMMUNEKOD': 1813, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1813},
                    8976: {'NO_KOMMUNEKOD': 1816, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1816},
                    8980: {'NO_KOMMUNEKOD': 1815, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1815},
                    8981: {'NO_KOMMUNEKOD': 1815, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1815},
                    8985: {'NO_KOMMUNEKOD': 1815, 'hdi': 441, 'NO_MODUL1': 501, 'district': 6, 'NO_kreg': 1893, 'New_Fylke': 18, 'New_kommune': 1815},
                    9000: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9001: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9002: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9006: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9007: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9008: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9009: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9010: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9011: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9012: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9013: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9014: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9015: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9016: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9017: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9018: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9019: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9020: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9022: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9024: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9027: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9029: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9030: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9034: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9037: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9038: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9040: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9042: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9043: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9046: {'NO_KOMMUNEKOD': 1939, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5425},
                    9049: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9050: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9055: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9056: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9059: {'NO_KOMMUNEKOD': 1933, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5422},
                    9060: {'NO_KOMMUNEKOD': 1938, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5424},
                    9062: {'NO_KOMMUNEKOD': 1938, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5424},
                    9064: {'NO_KOMMUNEKOD': 1938, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5424},
                    9068: {'NO_KOMMUNEKOD': 1938, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5424},
                    9069: {'NO_KOMMUNEKOD': 1938, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5424},
                    9080: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9100: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9103: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9104: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9106: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9107: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9110: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9118: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9119: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9120: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9128: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9130: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9131: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9132: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9134: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9135: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9136: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9137: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9138: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9140: {'NO_KOMMUNEKOD': 1936, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5423},
                    9141: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9143: {'NO_KOMMUNEKOD': 1939, 'hdi': 532, 'NO_MODUL1': 520, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5425},
                    9144: {'NO_KOMMUNEKOD': 1940, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5426},
                    9146: {'NO_KOMMUNEKOD': 1940, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5426},
                    9147: {'NO_KOMMUNEKOD': 1940, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5426},
                    9148: {'NO_KOMMUNEKOD': 1940, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5426},
                    9151: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9152: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9153: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9156: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9159: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9161: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9162: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9163: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9169: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9170: {'NO_KOMMUNEKOD': 2111, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2111},
                    9171: {'NO_KOMMUNEKOD': 2111, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2111},
                    9173: {'NO_KOMMUNEKOD': 2111, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2111},
                    9174: {'NO_KOMMUNEKOD': 2131, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2131},
                    9175: {'NO_KOMMUNEKOD': 2111, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2111},
                    9176: {'NO_KOMMUNEKOD': 2121, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2121},
                    9178: {'NO_KOMMUNEKOD': 2111, 'hdi': 534, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 0, 'New_Fylke': 21, 'New_kommune': 2111},
                    9180: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9181: {'NO_KOMMUNEKOD': 1942, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5428},
                    9182: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9184: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9185: {'NO_KOMMUNEKOD': 1943, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5429},
                    9186: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9189: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9190: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9192: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9193: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9194: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9195: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9197: {'NO_KOMMUNEKOD': 1941, 'hdi': 533, 'NO_MODUL1': 522, 'district': 6, 'NO_kreg': 1995, 'New_Fylke': 54, 'New_kommune': 5427},
                    9200: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9251: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9252: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9253: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9254: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9255: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9256: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9257: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9258: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9259: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9260: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9261: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9262: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9265: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9266: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9267: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9268: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9269: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9270: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9271: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9272: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9275: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9276: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9277: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9278: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9279: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9280: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9281: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9283: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9284: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9285: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9286: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9287: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9288: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9290: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9291: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9292: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9293: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9294: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9296: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9298: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9299: {'NO_KOMMUNEKOD': 1902, 'hdi': 532, 'NO_MODUL1': 521, 'district': 6, 'NO_kreg': 1992, 'New_Fylke': 54, 'New_kommune': 5401},
                    9300: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9302: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9303: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9304: {'NO_KOMMUNEKOD': 1927, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9305: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9310: {'NO_KOMMUNEKOD': 1925, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5419},
                    9311: {'NO_KOMMUNEKOD': 1926, 'hdi': 534, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5420},
                    9315: {'NO_KOMMUNEKOD': 1925, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5419},
                    9316: {'NO_KOMMUNEKOD': 1926, 'hdi': 534, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5420},
                    9321: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9322: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9325: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9326: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9327: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9329: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9334: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9335: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9336: {'NO_KOMMUNEKOD': 1924, 'hdi': 531, 'NO_MODUL1': 519, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5418},
                    9350: {'NO_KOMMUNEKOD': 1923, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5417},
                    9355: {'NO_KOMMUNEKOD': 1923, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5417},
                    9357: {'NO_KOMMUNEKOD': 1920, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5415},
                    9358: {'NO_KOMMUNEKOD': 1920, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5415},
                    9360: {'NO_KOMMUNEKOD': 1922, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5416},
                    9365: {'NO_KOMMUNEKOD': 1922, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5416},
                    9370: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9372: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9373: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9380: {'NO_KOMMUNEKOD': 1928, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9381: {'NO_KOMMUNEKOD': 1928, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9384: {'NO_KOMMUNEKOD': 1929, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9385: {'NO_KOMMUNEKOD': 1929, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9386: {'NO_KOMMUNEKOD': 1929, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9388: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9389: {'NO_KOMMUNEKOD': 1931, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9392: {'NO_KOMMUNEKOD': 1927, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9395: {'NO_KOMMUNEKOD': 1928, 'hdi': 531, 'NO_MODUL1': 518, 'district': 6, 'NO_kreg': 1994, 'New_Fylke': 54, 'New_kommune': 5421},
                    9400: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9402: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9403: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9404: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9405: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9406: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9407: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9408: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9409: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9411: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9414: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9415: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9419: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9420: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9423: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9424: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9425: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9426: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9427: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9430: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9436: {'NO_KOMMUNEKOD': 1852, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 54, 'New_kommune': 5412},
                    9439: {'NO_KOMMUNEKOD': 1913, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5412},
                    9440: {'NO_KOMMUNEKOD': 1913, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5412},
                    9441: {'NO_KOMMUNEKOD': 1852, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 54, 'New_kommune': 5412},
                    9442: {'NO_KOMMUNEKOD': 1852, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 54, 'New_kommune': 5412},
                    9443: {'NO_KOMMUNEKOD': 1852, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 54, 'New_kommune': 5412},
                    9444: {'NO_KOMMUNEKOD': 1852, 'hdi': 521, 'NO_MODUL1': 508, 'district': 6, 'NO_kreg': 1892, 'New_Fylke': 54, 'New_kommune': 5412},
                    9445: {'NO_KOMMUNEKOD': 1913, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5412},
                    9446: {'NO_KOMMUNEKOD': 1913, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5412},
                    9450: {'NO_KOMMUNEKOD': 1917, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5413},
                    9453: {'NO_KOMMUNEKOD': 1917, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5413},
                    9454: {'NO_KOMMUNEKOD': 1917, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5413},
                    9455: {'NO_KOMMUNEKOD': 1917, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5413},
                    9470: {'NO_KOMMUNEKOD': 1919, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5414},
                    9471: {'NO_KOMMUNEKOD': 1919, 'hdi': 524, 'NO_MODUL1': 517, 'district': 6, 'NO_kreg': 1993, 'New_Fylke': 54, 'New_kommune': 5414},
                    9475: {'NO_KOMMUNEKOD': 1911, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5411},
                    9476: {'NO_KOMMUNEKOD': 1911, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5411},
                    9479: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9480: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9481: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9482: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9483: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9484: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9485: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9486: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9487: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9488: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9489: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9496: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9497: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9498: {'NO_KOMMUNEKOD': 1903, 'hdi': 523, 'NO_MODUL1': 515, 'district': 6, 'NO_kreg': 1991, 'New_Fylke': 54, 'New_kommune': 5402},
                    9501: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9502: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9503: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9504: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9505: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9506: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9507: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9508: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9509: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9510: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9511: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9512: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9513: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9514: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9515: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9516: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9517: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9518: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9519: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9520: {'NO_KOMMUNEKOD': 2011, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5430},
                    9521: {'NO_KOMMUNEKOD': 2011, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5430},
                    9525: {'NO_KOMMUNEKOD': 2011, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5430},
                    9531: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9532: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9533: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9536: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9540: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9545: {'NO_KOMMUNEKOD': 2012, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5403},
                    9550: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9580: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9582: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9583: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9584: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9585: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9586: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9587: {'NO_KOMMUNEKOD': 2014, 'hdi': 541, 'NO_MODUL1': 523, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5432},
                    9590: {'NO_KOMMUNEKOD': 2015, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5433},
                    9593: {'NO_KOMMUNEKOD': 2015, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5433},
                    9595: {'NO_KOMMUNEKOD': 2015, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2093, 'New_Fylke': 54, 'New_kommune': 5433},
                    9600: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9609: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9610: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9613: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9615: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9616: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9620: {'NO_KOMMUNEKOD': 2017, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9621: {'NO_KOMMUNEKOD': 2017, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9624: {'NO_KOMMUNEKOD': 2017, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9650: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9657: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9664: {'NO_KOMMUNEKOD': 2004, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9670: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9672: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9690: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9691: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9692: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9700: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9709: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9710: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9711: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9712: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9713: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9714: {'NO_KOMMUNEKOD': 2018, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5434},
                    9715: {'NO_KOMMUNEKOD': 2017, 'hdi': 542, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5406},
                    9716: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9717: {'NO_KOMMUNEKOD': 2022, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5438},
                    9722: {'NO_KOMMUNEKOD': 2020, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5436},
                    9730: {'NO_KOMMUNEKOD': 2021, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5437},
                    9735: {'NO_KOMMUNEKOD': 2021, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5437},
                    9740: {'NO_KOMMUNEKOD': 2022, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5438},
                    9742: {'NO_KOMMUNEKOD': 2022, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5438},
                    9750: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9751: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9760: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9763: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9764: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9765: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 524, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9768: {'NO_KOMMUNEKOD': 2019, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5435},
                    9770: {'NO_KOMMUNEKOD': 2023, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5439},
                    9771: {'NO_KOMMUNEKOD': 2023, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5439},
                    9772: {'NO_KOMMUNEKOD': 2023, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5439},
                    9773: {'NO_KOMMUNEKOD': 2023, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5439},
                    9775: {'NO_KOMMUNEKOD': 2023, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5439},
                    9782: {'NO_KOMMUNEKOD': 2022, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5438},
                    9790: {'NO_KOMMUNEKOD': 2022, 'hdi': 543, 'NO_MODUL1': 525, 'district': 6, 'NO_kreg': 2092, 'New_Fylke': 54, 'New_kommune': 5438},
                    9800: {'NO_KOMMUNEKOD': 2003, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5405},
                    9802: {'NO_KOMMUNEKOD': 2003, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5405},
                    9810: {'NO_KOMMUNEKOD': 2003, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5405},
                    9811: {'NO_KOMMUNEKOD': 2003, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5405},
                    9815: {'NO_KOMMUNEKOD': 2003, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5405},
                    9820: {'NO_KOMMUNEKOD': 2027, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5442},
                    9826: {'NO_KOMMUNEKOD': 2025, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5441},
                    9840: {'NO_KOMMUNEKOD': 2027, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5442},
                    9845: {'NO_KOMMUNEKOD': 2025, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5441},
                    9846: {'NO_KOMMUNEKOD': 2025, 'hdi': 544, 'NO_MODUL1': 527, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5441},
                    9900: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9910: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9912: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9914: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9915: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9916: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9917: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9925: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9930: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9935: {'NO_KOMMUNEKOD': 2030, 'hdi': 546, 'NO_MODUL1': 528, 'district': 6, 'NO_kreg': 2094, 'New_Fylke': 54, 'New_kommune': 5444},
                    9950: {'NO_KOMMUNEKOD': 2002, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5404},
                    9951: {'NO_KOMMUNEKOD': 2002, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5404},
                    9960: {'NO_KOMMUNEKOD': 2002, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5404},
                    9980: {'NO_KOMMUNEKOD': 2024, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5440},
                    9981: {'NO_KOMMUNEKOD': 2024, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5440},
                    9982: {'NO_KOMMUNEKOD': 2024, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5440},
                    9990: {'NO_KOMMUNEKOD': 2028, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5443},
                    9991: {'NO_KOMMUNEKOD': 2028, 'hdi': 545, 'NO_MODUL1': 526, 'district': 6, 'NO_kreg': 2091, 'New_Fylke': 54, 'New_kommune': 5443}}

    return valueDict

#calling functions to run
if __name__=='__main__':
    pathSample = r'R:\Sample'
    pathSampleOld = r'R:\Sample\old'
    # main('dk', 1063, pathSample, pathSampleOld)
    # main('dk', 1068, pathSample, pathSampleOld)
    for period in range(1065, 1075):
        main('dk', period, pathSample, pathSampleOld)