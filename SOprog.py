import tkinter as tk
from PIL import Image, ImageTk
import os
import master_file
import pandas as pd
import datetime

def guess_period():
    import datetime
    today = str(datetime.date.today())
    y, m, d = int(today[:4]), int(today[5:7]), int(today[8:])
    datetime = datetime.date(y, m, d).isocalendar()
    y = int(datetime[0])
    w = int(datetime[1])
    d = int(datetime[2])
    years = ((2014, 785, 836), (2015, 837, 889), (2016, 890, 941), (2017, 942, 993), (2018, 994, 1045), (2019, 1046, 1097), (2020, 1098, 1150), (2021, 1151, 1202), (2022, 1203, 1254))
    for i in years:
        if y == i[0]:
            if d > 3:
                period_guess = i[1]+w-1
            else:
                period_guess = i[1]+w-2
    return period_guess

def calc_week(period):
    import numpy as np
    years = ((2013,733,784),(2014,785,836),(2015,837,889),(2016,890,941),(2017,942,993),(2018,994,1045),(2019,1046,1097),(2020,1098,1150))
    week = 0
    if period == np.nan:
        return np.nan
    else:
        for i in years:
            if period >= i[1] and period <= i[2]:
                if period - i[1] + 1 < 10:
                    week = str(i[0]) + '0' + str(period - i[1] + 1)
                else:
                    week = str(i[0])+str(period - i[1] + 1)
        return week

# Calculation of MADRAS period based on YearWeek format
def calc_period(week):
    years = (
        (2013, 733, 784), (2014, 785, 836), (2015, 837, 889), (2016, 890, 941), (2017, 942, 993), (2018, 994, 1045),
        (2019, 1046, 1097), (2020, 1098, 1150))
    weekToString = str(week)
    weekToPeriod = 0
    for i in years:
        if weekToString[:4] == str(i[0]):
            if weekToString[4] == "0":
                weekToPeriod = int(weekToString[5]) + i[1] - 1
            else:
                weekToPeriod = int(weekToString[4:]) + i[1] - 1

    return weekToPeriod

def sendmail(user, password, to, title, mail, *args, attachment=''):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import smtplib

    if len(args) == 1 and isinstance(args[0], list):# == type([]):
        args = args[0]

    msg = MIMEMultipart()
    msg['From'] = user
    to = to.split(',')
    msg['To'] = ", ".join(to)
    msg['Subject'] = title
    msg.attach(MIMEText(mail, 'plain'))

    for i in args:
        if i[1].empty == False:
            html = i[1].to_html(index=False, justify='left')
            if i[0] != '':
                msg.attach(MIMEText('\n\n', 'plain'))
                msg.attach(MIMEText('<strong>'+i[0]+'</strong>  ', 'html'))
            msg.attach(MIMEText(html, 'html'))

    if attachment != '':
        for file in attachment.split(','):
            file = file.strip()
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((open(file, 'rb')).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', 'attachment; filename = %s' % attachment.split('\\')[-1])
            msg.attach(p)

    import aaa
    pas = aaa.pas(user, password)

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    try:
        server.login(user, pas)
        server.sendmail(user, to, msg.as_string())
        server.quit()
        showmessage('Sent', 'Mail with output sent successfully')
    except:
        showmessage('Error', 'Wrong user or password')

def showmessage(Title, msg):
    from tkinter import messagebox as msgbox
    root = tk.Tk()
    root.withdraw()
    msgbox.showinfo(' '+Title, msg)
    root.destroy()

class showoutput2:
    def __init__(self, title, *args):
        import pandastable as pdt

        if len(args) == 1 and isinstance(args[0], list):  # == type([]):
            args = args[0]

        self.top = tk.Toplevel()
        self.top.title(' '+title)
        self.args = args
        self.ShowDownload = False
        self.ShowMail = False
        self.dataframes = self.dfs([])
        self.nr = 0
        self.Check = 0
        # self.wanted = []
        self.path = tk.StringVar(value='')#tk.StringVar(value=os.path.join(os.path.dirname(__file__), r"temp\output.xlsx"))

        def onFrameConfigure(event, canvas):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.delete("all")
            # w, h = event.width, event.height
            w = self.TopFrame.winfo_width()
            drawtables(w)
        def mouse_scroll(event, canvas):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
            else:
                if event.num == 5:
                    move = 1
                else:
                    move = -1

        self.TopFrame = tk.Frame(self.top, width=600, height=500)
        self.TopFrame.pack(fill='both', expand=1)
        self.TopFrame.pack_propagate(0)

        self.SaveFrame = tk.Frame(self.TopFrame, bd=1, relief='groove')
        self.SaveFile = window.save_file_button(self.SaveFrame, 'Output from '+title, '.xlsx', self.save_xls)

        self.MailFrame = tk.Frame(self.TopFrame, bd=1, relief='groove')

        self.MailFrame1 = tk.Frame(self.MailFrame)
        self.FromLbl = tk.Label(self.MailFrame1, text='From:')
        self.var_from_mail = tk.StringVar()
        self.var_from_mail.set('@nielsen.com')
        self.entry_from = tk.Entry(self.MailFrame1, textvariable=self.var_from_mail, width=32)
        self.PassLbl = tk.Label(self.MailFrame1, text='Password:')
        self.var_pass = tk.StringVar()
        self.var_pass.set('')
        self.entry_pass = tk.Entry(self.MailFrame1, show='*', textvariable=self.var_pass, width=12)
        self.ToLbl = tk.Label(self.MailFrame1, text='To:')
        self.var_to_mail = tk.StringVar()
        self.var_to_mail.set('use "," as separator | e.g. aaa@nielsen.com, bbb@gmail.com')
        self.entry_to = tk.Entry(self.MailFrame1, textvariable=self.var_to_mail, width=54)
        self.FavLbl =  self.favorites_button(self.MailFrame1, self.var_to_mail)
        # space1 = tk.Label(self.MailFrame1, height=1)
        self.TitleLbl = tk.Label(self.MailFrame1, text='Title')
        self.var_title = tk.StringVar()
        self.var_title.set('Output from '+title)
        self.entry_title = tk.Entry(self.MailFrame1, textvariable=self.var_title, width=60)
        self.MailLbl = tk.Label(self.MailFrame1, text='Mail')
        from tkinter import scrolledtext as scrtxt
        self.entry_mail = scrtxt.ScrolledText(self.MailFrame1, width=45, height=6)
        self.entry_mail.insert('insert', "Hello,\n\nI'm sending output from {program}\n\nRegards,\n".format(program=title))

        self.MailFrame2 = tk.Frame(self.MailFrame)
        self.ChooseLbl = tk.Label(self.MailFrame2, text='Choose outputs:')
        self.AttachLbl = tk.Label(self.MailFrame2, text='How to attach:')
        self.AsTextCheckVar = tk.IntVar(value=1)
        self.AsTextCheck = tk.Checkbutton(self.MailFrame2, text='in mail', variable=self.AsTextCheckVar, command=self.attachtext)
        self.AsTextCheck.select()
        self.ExcelCheckVar = tk.IntVar(value=0)
        self.ExcelCheck = tk.Checkbutton(self.MailFrame2, text='as .xlsx file', variable=self.ExcelCheckVar, command=self.attachexcel)
        self.SendButton = window.send_mail_button(self.MailFrame2, self.var_from_mail, self.var_pass, self.var_to_mail, self.var_title, self.entry_mail, self.dataframes, self.path, self.save_xls)

        self.MailFrame1.pack(side='left')
        self.FromLbl.grid(row=0, column=0, sticky='e')
        self.entry_from.grid(row=0, column=1, sticky='w')
        self.PassLbl.grid(row=0, column=2, sticky='e')
        self.entry_pass.grid(row=0, column=3, sticky='w')
        self.ToLbl.grid(row=1, column=0, sticky='ne')
        self.entry_to.grid(row=1, column=1, columnspan=3, sticky='nw')
        self.FavLbl.Button.grid(row=1, column=3, padx=(0, 17), sticky='ne')
        # space1.grid(row=2)
        self.TitleLbl.grid(row=3, column=0, sticky='e')
        self.entry_title.grid(row=3, column=1, columnspan=3, sticky='w')
        self.MailLbl.grid(row=4, column=0, sticky='ne')
        self.entry_mail.grid(row=4, column=1, columnspan=3, sticky='w')

        self.MailFrame2.pack(fill='both', expand=1, side='right')
        self.ChooseLbl.grid(row=0, column=1, sticky='w')
        self.AttachLbl.grid(row=0, column=0, sticky='w')
        self.AsTextCheck.grid(row=1, column=0, sticky='w')
        self.ExcelCheck.grid(row=2, column=0, sticky='w')

        self.ButtonFrame = tk.Frame(self.TopFrame)
        self.ButtonFrame.pack(fill='x', expand=0, side='top')

        self.SaveButton = tk.Button(self.ButtonFrame, text='Save to .xlsx', bd=3, relief='ridge', overrelief='groove', command=lambda: self.show_download())
        self.SaveButton.pack(side='left', fill='x', expand=1)

        self.MailButton = tk.Button(self.ButtonFrame, text='Send via email', bd=3, relief='ridge', overrelief='groove', command=lambda: self.show_mail())
        self.MailButton.pack(side='right', fill='x', expand=1)

        self.CanvasFrame = tk.Frame(self.TopFrame)
        self.CanvasFrame.pack(fill='both', expand=1, side='bottom')

        self.ScrollBar = tk.Scrollbar(self.CanvasFrame)
        self.canvas = tk.Canvas(self.CanvasFrame, yscrollcommand=self.ScrollBar.set)
        self.ScrollBar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=1)
        self.ScrollBar.config(command=self.canvas.yview)

        self.canvas.bind('<Configure>', lambda event, canvas=self.canvas: onFrameConfigure(event, canvas))
        self.TopFrame.bind_all('<MouseWheel>', lambda event, canvas=self.canvas: mouse_scroll(event, canvas))

        def drawtables(width):
            self.MainFrame = tk.Frame(self.canvas)
            self.MainFrame.pack(fill='both', expand=1)
            self.canvas.create_window((0, 0), window=self.MainFrame, anchor='nw')
            for i in self.args:
                if i[1].empty == False:
                    rows = len(i[1].index)
                    if rows > 30:
                        rows = 30
                    TableFrame = tk.Frame(self.MainFrame, height=110+rows*20, width=width-20)
                    TableFrame.pack(fill='both', expand=1)
                    TableFrame.pack_propagate(0)
                    if i[0] != '':
                        FrameMsg = tk.Frame(TableFrame)
                        FrameMsg.pack(fill='x')
                        Label = tk.Label(FrameMsg, text='\n'+i[0])
                        Label.pack(side='left')

                    Frame = tk.Frame(TableFrame)
                    Frame.pack(fill='both', expand=1)
                    Table = pdt.Table(Frame, dataframe=i[1])
                    Table.show()
                    try:
                        Table.rowcolors = i[2]
                        Table.redraw()
                    except IndexError:
                        pass
        for i in self.args:
            if i[1].empty == False:
                self.nr += 1
                # self.wanted.append(1)
                self.dataframes.append(i)

                exec("self.CheckVar{nr} = tk.IntVar(value=1)".format(nr=self.nr))
                exec(r"Check{nr} = tk.Checkbutton(self.SaveFrame, text=i[0].split('\n')[0], variable=self.CheckVar{nr}, command=self.onCheckButton)".format(nr=self.nr))
                exec(r"Check{nr}.select()".format(nr=self.nr))
                exec("Check{nr}.grid(row={nr}, column=0, sticky='w', padx=(5, 50))".format(nr=self.nr))
                exec(r"CheckM{nr} = tk.Checkbutton(self.MailFrame2, text=i[0].split('\n')[0], variable=self.CheckVar{nr}, command=self.onCheckButton)".format(nr=self.nr))
                exec(r"CheckM{nr}.select()".format(nr=self.nr))
                exec("CheckM{nr}.grid(row={nr}, column=1, sticky='w')".format(nr=self.nr))

            self.SaveFile.Button.grid(row=1, column=1, rowspan=self.nr+1)
            self.SendButton.Button.grid(row=3, column=0, rowspan=self.nr+1, sticky='w')

        drawtables(self.TopFrame.winfo_width()-20)
        # self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.quit())
        # self.root.mainloop()
    class dfs:
        def __init__(self, dfs):
            self.dfs = dfs
        def get(self):
            return self.dfs
        def set(self, dfs):
            self.dfs = dfs
        def append(self, dfs):
            self.dfs.append(dfs)

    class favorites_button:
        def __init__(self, Frame, entry):
            self.ico = Image.open(os.path.join(os.path.dirname(__file__), "IMG/fav.png"))
            self.ico = self.ico.resize((34, 34))
            self.img = ImageTk.PhotoImage(self.ico)

            self.Button = tk.Button(Frame, command=lambda: self.set_favourites(entry))
            self.Button.config(image=self.img)

        def set_favourites(self, entry):
            self.favtop = tk.Toplevel(height=280, width=250)
            self.favtop.title(' Add mails')
            self.favtop.pack_propagate(0)

            self.MetteVar = tk.IntVar(value=0)
            self.ThomasVar = tk.IntVar(value=0)
            self.JuliaVar = tk.IntVar(value=0)
            self.mscinorwayVar = tk.IntVar(value=0)
            self.WeronikaVar = tk.IntVar(value=0)
            self.GrzegorzVar = tk.IntVar(value=0)
            self.WojtekVar = tk.IntVar(value=0)
            self.SebastianVar = tk.IntVar(value=0)
            self.NOCSOVar = tk.IntVar(value=0)

            favourites = {'mette.holst@nielsen.com': self.MetteVar,
                          'thomas.christiansen@nielsen.com': self.ThomasVar,
                          'julia.reenberg@nielsen.com': self.JuliaVar,
                          'msci.norway@nielsen.com': self.mscinorwayVar,
                          'weronika.gorska@nielsen.com': self.WeronikaVar,
                          'grzegorz.laskowski@nielsen.com': self.GrzegorzVar,
                          'wojciech.piotrowski@nielsen.com': self.WojtekVar,
                          'sebastian.konicz@nielsen.com': self.SebastianVar,
                          'nielsenoperationscenterwarsawnordicsbauso@nielsen.com': self.NOCSOVar,
                          }

            mail_to = entry.get().replace(' ', '').split(',')
            for mail in mail_to:
                if mail in favourites.keys():
                    favourites[mail].set(1)

            MetteBut = tk.Checkbutton(self.favtop, text='Mette Holst', variable=self.MetteVar)#mette.holst@nielsen.com
            ThomasBut = tk.Checkbutton(self.favtop, text='Thomas Christiansen', variable=self.ThomasVar)#thomas.christiansen@nielsen.com
            JuliaBut = tk.Checkbutton(self.favtop, text='Julia Reenberg', variable=self.JuliaVar)#julia.reenberg@nielsen.com
            mscinorwayBut = tk.Checkbutton(self.favtop, text='MSci Norway', variable=self.mscinorwayVar)#msci.norway@nielsen.com
            WeronikaBut = tk.Checkbutton(self.favtop, text='Weronika Górska', variable=self.WeronikaVar)#weronika.gorska@nielsen.com
            GrzegorzBut = tk.Checkbutton(self.favtop, text='Grzegorz Laskowski', variable=self.GrzegorzVar)#grzegorz.laskowski@nielsen.com
            WojtekBut = tk.Checkbutton(self.favtop, text='Wojciech Piotrowski', variable=self.WojtekVar)#wojciech.piotrowski@nielsen.com
            SebastianBut = tk.Checkbutton(self.favtop, text='Sebastian Konicz', variable=self.SebastianVar)#sebastian.konicz@nielsen.com
            NOCSOBut = tk.Checkbutton(self.favtop, text='NOC SO', variable=self.NOCSOVar)#nielsenoperationscenterwarsawnordicsbauso@nielsen.com

            MetteBut.pack(side='top', anchor='w', padx=(10,0))
            ThomasBut.pack(side='top', anchor='w', padx=(10,0))
            JuliaBut.pack(side='top', anchor='w', padx=(10,0))
            mscinorwayBut.pack(side='top', anchor='w', padx=(10,0))
            WeronikaBut.pack(side='top', anchor='w', padx=(10,0))
            GrzegorzBut.pack(side='top', anchor='w', padx=(10,0))
            WojtekBut.pack(side='top', anchor='w', padx=(10,0))
            SebastianBut.pack(side='top', anchor='w', padx=(10,0))
            NOCSOBut.pack(side='top', anchor='w', padx=(10,0))

            ApplyBut = self.add_button(self.favtop, entry, favourites)
            ApplyBut.Button.pack(side='bottom')

        class add_button:
            def __init__(self, Frame, entry, favourites):
                self.ico = Image.open(os.path.join(os.path.dirname(__file__), r"IMG\mailadd.png"))
                self.ico = self.ico.resize((40, 40), resample=Image.LANCZOS)
                self.img = ImageTk.PhotoImage(self.ico)

                self.Button = tk.Button(Frame, text='add!', command=lambda: self.add(Frame, entry, favourites))
                self.Button.config(image=self.img)
            def add(self, frame, entry, favourites):
                if entry.get() == 'use "," as separator | e.g. aaa@nielsen.com, bbb@gmail.com':
                    entry.set('')
                mail_to = entry.get().replace(' ', '').split(',')
                new_mail_to = ''
                for mail in mail_to:
                    if mail not in favourites.keys() and mail_to[0] != '':
                        new_mail_to += mail + ', '
                    elif mail in favourites.keys() and favourites[mail].get() == 1:
                        new_mail_to += mail + ', '
                for mail in favourites.keys():
                    if favourites[mail].get() == 1 and mail not in new_mail_to.replace(' ','').split(','):
                        new_mail_to += mail + ', '
                entry.set(new_mail_to[:-2])
                frame.destroy()

    def attachtext(self):
        if self.AsTextCheckVar.get() == 0:
            self.dataframes.set([])
        elif self.AsTextCheckVar.get() == 1:
            nr = 0
            self.dataframes.set([])
            for i in self.args:
                if i[1].empty == False:
                    nr += 1
                    exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                    if self.Check == 1:
                        self.dataframes.append(i)
    def attachexcel(self):
        if self.ExcelCheckVar.get() == 0:
            self.path.set('')
        elif self.ExcelCheckVar.get() == 1:
            self.path.set(os.path.join(os.path.dirname(__file__), r"temp\output.xlsx"))
    def onCheckButton(self):
        if self.AsTextCheckVar.get() == 0:
            self.dataframes.set([])
        elif self.AsTextCheckVar.get() == 1:
            nr = 0
            self.dataframes.set([])
            for i in self.args:
                if i[1].empty == False:
                    nr += 1
                    exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                    if self.Check == 1:
                        self.dataframes.append(i)
    def show_download(self):
        if self.ShowDownload == True:
            self.ShowDownload = False
            self.SaveButton.configure(relief='ridge')
            self.SaveFrame.pack_forget()
        elif self.ShowDownload == False:
            self.ShowDownload = True
            self.SaveButton.configure(relief='sunken')
            self.MailButton.configure(relief='ridge')
            self.ShowMail = False
            self.MailFrame.pack_forget()
            self.SaveFrame.pack(fill='both', expand=0, side='top')
    def show_mail(self):
        if self.ShowMail == True:
            self.ShowMail = False
            self.MailButton.configure(relief='ridge')
            self.MailFrame.pack_forget()
        elif self.ShowMail == False:
            self.ShowMail = True
            self.MailButton.configure(relief='sunken')
            self.SaveButton.configure(relief='ridge')
            self.ShowDownload = False
            self.SaveFrame.pack_forget()
            self.MailFrame.pack(fill='both', expand=0, side='top')
    def save_xls(self, Path):
        writer = pd.ExcelWriter(Path, engine='xlsxwriter')
        nr = 0
        for i in self.args:
            if i[1].empty == False:
                nr += 1
                exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                if self.Check == 1:
                    sheetname = i[0].split('\n')[0]
                    if len(sheetname) > 30:
                        sheetname = sheetname[:30]
                    for s in '[]:*?/\\':
                        sheetname = sheetname.replace(s, '_')
                    i[1].to_excel(writer, sheet_name=sheetname, index=False)
        try:
            writer.save()
        except:
            pass

class showoutput3:
    def __init__(self, root, *args):
        import pandastable as pdt

        if len(args) == 1 and isinstance(args[0], list):  # == type([]):
            args = args[0]

        self.root = root
        self.args = args
        self.ShowDownload = False
        self.ShowMail = False
        self.dataframes = self.dfs([])
        self.nr = 0
        self.Check = 0
        self.path = tk.StringVar(value='')#tk.StringVar(value=os.path.join(os.path.dirname(__file__), r"temp\output.xlsx"))

        def onFrameConfigure(event, canvas):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.delete("all")
            # w, h = event.width, event.height
            w = self.TopFrame.winfo_width()
            drawtables(w)
        def mouse_scroll(event, canvas):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
            else:
                if event.num == 5:
                    move = 1
                else:
                    move = -1

        self.TopFrame = tk.Frame(self.root, width=600, height=500)
        self.TopFrame.pack(fill='both', expand=1)
        self.TopFrame.pack_propagate(0)

        self.SaveFrame = tk.Frame(self.TopFrame, bd=1, relief='groove')
        self.SaveFile = window.save_file_button(self.SaveFrame, 'Output from'+self.root.title(), '.xlsx', self.save_xls)

        self.MailFrame = tk.Frame(self.TopFrame, bd=1, relief='groove')

        self.MailFrame1 = tk.Frame(self.MailFrame)
        self.FromLbl = tk.Label(self.MailFrame1, text='From:')
        self.var_from_mail = tk.StringVar(value='wojciech.piotrowski@nielsen.com')
        # self.var_from_mail.set('wojciech.piotrowski@nielsen.com')
        self.entry_from = tk.Entry(self.MailFrame1, textvariable=self.var_from_mail, width=32)
        self.PassLbl = tk.Label(self.MailFrame1, text='Password:')
        self.var_pass = tk.StringVar()
        self.var_pass.set('')
        self.entry_pass = tk.Entry(self.MailFrame1, show='*', textvariable=self.var_pass, width=12)
        self.ToLbl = tk.Label(self.MailFrame1, text='To:')
        self.var_to_mail = tk.StringVar(value='please use "," as separator | e.g. aaa@nielsen.com, bbb@gmail.com')
        # self.var_to_mail.set('please use "," as separator | e.g. aaa@nielsen.com, bbb@gmail.com')
        # self.var_to_mail.set('woojtoo@gmail.com')
        self.entry_to = tk.Entry(self.MailFrame1, textvariable=self.var_to_mail, width=60)
        space1 = tk.Label(self.MailFrame1, height=1)
        self.TitleLbl = tk.Label(self.MailFrame1, text='Title')
        self.var_title = tk.StringVar(value='Output from '+self.root.title())
        # self.var_title.set('Output from '+self.root.title())
        self.entry_title = tk.Entry(self.MailFrame1, textvariable=self.var_title, width=60)
        self.MailLbl = tk.Label(self.MailFrame1, text='Mail')
        from tkinter import scrolledtext as scrtxt
        self.entry_mail = scrtxt.ScrolledText(self.MailFrame1, width=45, height=6)
        self.entry_mail.insert('insert', "Hello,\n\nI'm sending output from {program}\n\nRegards,\n".format(program=self.root.title()))

        self.MailFrame2 = tk.Frame(self.MailFrame)
        self.ChooseLbl = tk.Label(self.MailFrame2, text='Choose outputs:')
        self.AttachLbl = tk.Label(self.MailFrame2, text='How to attach:')
        self.AsTextCheckVar = tk.IntVar(value=1)
        self.AsTextCheck = tk.Checkbutton(self.MailFrame2, text='in mail', variable=self.AsTextCheckVar, command=self.attachtext)
        self.AsTextCheck.select()
        self.ExcelCheckVar = tk.IntVar(value=0)
        self.ExcelCheck = tk.Checkbutton(self.MailFrame2, text='as .xlsx file', variable=self.ExcelCheckVar, command=self.attachexcel)
        self.SendButton = window.send_mail_button(self.MailFrame2, self.var_from_mail, self.var_pass, self.var_to_mail, self.var_title, self.entry_mail, self.dataframes, self.path, self.save_xls)

        self.MailFrame1.pack(side='left')
        self.FromLbl.grid(row=0, column=0, sticky='e')
        self.entry_from.grid(row=0, column=1, sticky='w')
        self.PassLbl.grid(row=0, column=2, sticky='e')
        self.entry_pass.grid(row=0, column=3, sticky='w')
        self.ToLbl.grid(row=1, column=0, sticky='e')
        self.entry_to.grid(row=1, column=1, columnspan=3, sticky='w')
        space1.grid(row=2)
        self.TitleLbl.grid(row=3, column=0, sticky='e')
        self.entry_title.grid(row=3, column=1, columnspan=3, sticky='w')
        self.MailLbl.grid(row=4, column=0, sticky='ne')
        self.entry_mail.grid(row=4, column=1, columnspan=3, sticky='w')

        self.MailFrame2.pack(fill='both', expand=1, side='right')
        self.ChooseLbl.grid(row=0, column=1, sticky='w')
        self.AttachLbl.grid(row=0, column=0, sticky='w')
        self.AsTextCheck.grid(row=1, column=0, sticky='w')
        self.ExcelCheck.grid(row=2, column=0, sticky='w')

        self.ButtonFrame = tk.Frame(self.TopFrame)
        self.ButtonFrame.pack(fill='x', expand=0, side='top')

        self.SaveButton = tk.Button(self.ButtonFrame, text='Save to .xlsx', bd=3, relief='ridge', overrelief='groove', command=lambda: self.show_download())
        self.SaveButton.pack(side='left', fill='x', expand=1)

        self.MailButton = tk.Button(self.ButtonFrame, text='Send via email', bd=3, relief='ridge', overrelief='groove', command=lambda: self.show_mail())
        self.MailButton.pack(side='right', fill='x', expand=1)

        self.CanvasFrame = tk.Frame(self.TopFrame)
        self.CanvasFrame.pack(fill='both', expand=1, side='bottom')

        self.ScrollBar = tk.Scrollbar(self.CanvasFrame)
        self.canvas = tk.Canvas(self.CanvasFrame, yscrollcommand=self.ScrollBar.set)
        self.ScrollBar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=1)
        self.ScrollBar.config(command=self.canvas.yview)

        self.canvas.bind('<Configure>', lambda event, canvas=self.canvas: onFrameConfigure(event, canvas))
        self.TopFrame.bind_all('<MouseWheel>', lambda event, canvas=self.canvas: mouse_scroll(event, canvas))

        def drawtables(width):
            self.MainFrame = tk.Frame(self.canvas)
            self.MainFrame.pack(fill='both', expand=1)
            self.canvas.create_window((0, 0), window=self.MainFrame, anchor='nw')
            for i in self.args:
                if i[1].empty == False:
                    rows = len(i[1].index)
                    # if rows > 10:
                    #     rows = 10
                    TableFrame = tk.Frame(self.MainFrame, height=110+rows*20, width=width-20)
                    TableFrame.pack(fill='both', expand=1)
                    TableFrame.pack_propagate(0)
                    if i[0] != '':
                        FrameMsg = tk.Frame(TableFrame)
                        FrameMsg.pack(fill='x')
                        Label = tk.Label(FrameMsg, text='\n'+i[0])
                        Label.pack(side='left')

                    Frame = tk.Frame(TableFrame)
                    Frame.pack(fill='both', expand=1)
                    Table = pdt.Table(Frame, dataframe=i[1])
                    Table.show()

        for i in self.args:
            if i[1].empty == False:
                self.nr += 1
                self.dataframes.append(i)

                exec("self.CheckVar{nr} = tk.IntVar(value=1)".format(nr=self.nr))
                exec(r"Check{nr} = tk.Checkbutton(self.SaveFrame, text=i[0].split('\n')[0], variable=self.CheckVar{nr}, command=self.onCheckButton)".format(nr=self.nr))
                exec(r"Check{nr}.select()".format(nr=self.nr))
                exec("Check{nr}.grid(row={nr}, column=0, sticky='w', padx=(5, 50))".format(nr=self.nr))
                exec(r"CheckM{nr} = tk.Checkbutton(self.MailFrame2, text=i[0].split('\n')[0], variable=self.CheckVar{nr}, command=self.onCheckButton)".format(nr=self.nr))
                exec(r"CheckM{nr}.select()".format(nr=self.nr))
                exec("CheckM{nr}.grid(row={nr}, column=1, sticky='w')".format(nr=self.nr))

            self.SaveFile.Button.grid(row=1, column=1, rowspan=self.nr+1)
            self.SendButton.Button.grid(row=3, column=0, rowspan=self.nr+1, sticky='w')

        drawtables(self.TopFrame.winfo_width()-20)

    class dfs:
        def __init__(self, dfs):
            self.dfs = dfs
        def get(self):
            return self.dfs
        def set(self, dfs):
            self.dfs = dfs
        def append(self, dfs):
            self.dfs.append(dfs)

    def attachtext(self):
        if self.AsTextCheckVar.get() == 0:
            self.dataframes.set([])
        elif self.AsTextCheckVar.get() == 1:
            nr = 0
            self.dataframes.set([])
            for i in self.args:
                if i[1].empty == False:
                    nr += 1
                    exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                    if self.Check == 1:
                        self.dataframes.append(i)
    def attachexcel(self):
        if self.ExcelCheckVar.get() == 0:
            self.path.set('')
        elif self.ExcelCheckVar.get() == 1:
            self.path.set(os.path.join(os.path.dirname(__file__), r"temp\output.xlsx"))
    def onCheckButton(self):
        if self.AsTextCheckVar.get() == 0:
            self.dataframes.set([])
        elif self.AsTextCheckVar.get() == 1:
            nr = 0
            self.dataframes.set([])
            for i in self.args:
                if i[1].empty == False:
                    nr += 1
                    exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                    if self.Check == 1:
                        self.dataframes.append(i)
    def show_download(self):
        if self.ShowDownload == True:
            self.ShowDownload = False
            self.SaveButton.configure(relief='ridge')
            self.SaveFrame.pack_forget()
        elif self.ShowDownload == False:
            self.ShowDownload = True
            self.SaveButton.configure(relief='sunken')
            self.MailButton.configure(relief='ridge')
            self.ShowMail = False
            self.MailFrame.pack_forget()
            self.SaveFrame.pack(fill='both', expand=0, side='top')
    def show_mail(self):
        if self.ShowMail == True:
            self.ShowMail = False
            self.MailButton.configure(relief='ridge')
            self.MailFrame.pack_forget()
        elif self.ShowMail == False:
            self.ShowMail = True
            self.MailButton.configure(relief='sunken')
            self.SaveButton.configure(relief='ridge')
            self.ShowDownload = False
            self.SaveFrame.pack_forget()
            self.MailFrame.pack(fill='both', expand=0, side='top')
    def save_xls(self, Path):
        writer = pd.ExcelWriter(Path, engine='xlsxwriter')
        nr = 0
        for i in self.args:
            if i[1].empty == False:
                nr += 1
                exec("self.Check = self.CheckVar{nr}.get()".format(nr=nr))
                if self.Check == 1:
                    i[1].to_excel(writer, sheet_name=i[0].split('\n')[0], index=False)
        try:
            writer.save()
        except:
            pass

def showoutput(root, *args):
    import pandastable as pdt

    def onFrameConfigure(canvas):
        canvas.configure(scrollregion=canvas.bbox("all"))
    def mouse_scroll(event, canvas):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        else:
            if event.num == 5:
                move = 1
            else:
                move = -1

    # root = tk.Tk(className=' '+Title)

    TopFrame = tk.Frame(root, width=600, height=500)
    TopFrame.pack(fill='both', expand=1)
    # TopFrame.pack_propagate(0)

    ScrollBar = tk.Scrollbar(TopFrame)
    canvas = tk.Canvas(TopFrame, yscrollcommand=ScrollBar.set)
    ScrollBar.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=1)
    ScrollBar.config(command=canvas.yview)

    MainFrame = tk.Frame(canvas)
    MainFrame.pack(fill='both', expand=1)
    canvas.create_window((0, 0), window=MainFrame, anchor='nw')
    canvas.bind('<Configure>', lambda event, canvas=canvas: onFrameConfigure(canvas))
    TopFrame.bind_all('<MouseWheel>', lambda event, canvas=canvas: mouse_scroll(event, canvas))
    for i in args:
        if i[1].empty == False:
            rows = len(i[1].index)
            # if rows > 10:
            #     rows = 10
            TableFrame = tk.Frame(MainFrame, height=100+rows*20, width=1400)
            TableFrame.pack(fill='both', expand=1)
            TableFrame.pack_propagate(0)
            if i[0] != '':
                FrameMsg = tk.Frame(TableFrame)
                FrameMsg.pack(fill='both', expand=1)
                Label = tk.Label(FrameMsg, text='\n'+i[0])
                Label.pack(side='left')

            Frame = tk.Frame(TableFrame)
            Frame.pack(fill='both', expand=1)
            Table = pdt.Table(Frame, dataframe=i[1])
            Table.show()

    # root.mainloop()

def showtable(root, *args):
    import pandastable as pdt

    # if isinstance(root, str):
    #     Title = root
    #     root = tk.Tk(className=Title)

    TopFrame = tk.Frame(root, width=600)#, height=500)
    TopFrame.pack(fill='both', expand=1)
    # TopFrame.pack_propagate(0)

    if len(args) == 1 and isinstance(args[0], list):# == type([]):
        args = args[0]
    for i in args:
        if i[1].empty == False:
            rows = len(i[1].index)
            if rows > 10:
                rows = 10
            MainFrame = tk.Frame(TopFrame, height=100 + rows * 20, width=450)
            MainFrame.pack(fill='both', expand=1)
            MainFrame.pack_propagate(0)

            if i[0] != '':
                FrameMsg = tk.Frame(MainFrame)
                FrameMsg.pack(fill='both', expand=1)
                Label = tk.Label(FrameMsg, text='\n'+i[0])
                Label.pack(side='left')

            Frame = tk.Frame(MainFrame)
            Frame.pack(fill='both', expand=1)
            Table = pdt.Table(Frame, dataframe=i[1])
            Table.show()

            Frame.config(height=20)

class window:
    def __init__(self, Title):
        self.Title = Title
        self.root = tk.Tk(className=' '+self.Title)
        self.root.iconbitmap(os.path.join(os.path.dirname(__file__), "IMG/rebel.ico"))

        self.period = guess_period()
        self.country = ''

        self.show_filter = False
        self.filter_country = '-'
        self.filter_period = '-'
        # self.filter_date = str(datetime.datetime.today()).split(' ')[0].split('-')[2] + '.' + \
        #                    str(datetime.datetime.today()).split(' ')[0].split('-')[1] + '.' + \
        #                    str(datetime.datetime.today()).split(' ')[0].split('-')[0]
        self.filter_date = 'YYYY-MM-DD'
        self.filter_year = 'YYYY'
        self.filter_month = 'MM'
        self.filter_day = 'DD'
        self.filter_state = '-'
        self.filter_program = '-'

        # Dropdown Menu
        self.dropdownmenu = tk.Menu(self.root)
        self.root.config(menu=self.dropdownmenu)
        # Checks
        self.checks = tk.Menu(self.dropdownmenu)
        self.dropdownmenu.add_cascade(label='Checks', menu=self.checks)
        self.checks.add_command(label='Legacy ACV', command=lambda: self.legacyacv())
        self.checks.add_command(label='Legacy Cells', command=lambda: self.legacycells())
        self.checks.add_command(label='Legacy MBD', command=lambda: self.legacyMBDs())
        self.checks.add_command(label='Eforte', command=lambda: self.eforte())
        self.checks.add_command(label='Estimation 2', command=lambda: self.estimation_2())
        # CIP Inputs
        self.inputs = tk.Menu(self.dropdownmenu)
        self.dropdownmenu.add_cascade(label='CIP Inputs', menu=self.inputs)
        self.inputs.add_command(label='01')  # , command=pass)
        self.inputs.add_command(label='02')  # , command=pass)
        self.inputs.add_command(label='03')  # , command=pass)
        self.inputs.add_command(label='04')  # , command=pass)
        self.inputs.add_command(label='05')  # , command=pass)
        self.inputs.add_command(label='06')  # , command=pass)
        self.inputs.add_command(label='07')  # , command=pass)
        self.inputs.add_command(label='08')  # , command=pass)
        self.inputs.add_command(label='09')  # , command=pass)
        self.inputs.add_command(label='10')  # , command=pass)
        # Other
        self.other = tk.Menu(self.dropdownmenu)
        self.dropdownmenu.add_cascade(label='Other', menu=self.other)
        self.other.add_command(label='MUS', command=lambda: self.mus())
        self.other.add_command(label='KPI for CSSI', command=lambda: self.kpi_cssi())
        self.c19 = tk.Menu(self.other)
        self.other.add_cascade(label='c19', menu=self.c19)
        self.c19.add_command(label='Causal cell industry after CSU', command=lambda: self.drutynacausala())
        self.c19.add_command(label='NonCensus cell industry after SI', command=lambda: self.drutynanoncensusa())
        self.denmark = tk.Menu(self.other)
        self.other.add_cascade(label='Denmark', menu=self.denmark)
        self.denmark.add_command(label='Cells', command=lambda: self.cellsdenmark())
        self.denmark.add_command(label='Hierarchies', command=lambda: self.hiidenmark())
        self.denmark.add_command(label='Causal sample selection', command=lambda: self.causal_sample_selection())
        self.other.add_separator()
        self.other.add_command(label='SQL queries', command=lambda: self.SQL_queries())
        self.other.add_separator()
        self.other.add_command(label='Log', command=lambda: self.tracebacklog())

        # Main Frame
        self.mainframe()
        self.img = Image.open(os.path.join(os.path.dirname(__file__), "IMG/n.png"))
        self.img = self.img.resize((600, 600), resample=Image.LANCZOS)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.bgimg = tk.Label(self.MainFrame, image=self.tkimg)
        self.bgimg.place(x=0, y=0, relwidth=1, relheight=1)

        self.InfoFrame = tk.Frame(self.root, bd=1, relief='groove')
        self.InfoFrame.pack(side='bottom', fill='x')

        self.CountryFrame = tk.Frame(self.InfoFrame)
        self.CountryFrame.pack(side='left')
        self.countryimage()
        self.BottomFrame = tk.Frame(self.InfoFrame)
        self.BottomFrame.pack(fill='x')

        self.InfoBarText = tk.StringVar()
        self.InfoBarText.set('Choose program')
        self.InfoBar = tk.Label(self.BottomFrame, textvariable=self.InfoBarText)
        self.InfoBar.pack(side='left')

        self.StateText = tk.StringVar()
        self.StateText.set('')
        self.State = tk.Label(self.BottomFrame, textvariable=self.StateText)
        self.State.pack(side='right')

        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.quit())
        self.root.mainloop()

    def mainframe(self):
        self.MainFrame = tk.Frame(self.root, width=600, height=500)
        self.MainFrame.pack_propagate(0)
        self.MainFrame.pack(fill='both', expand=1)

    def countryimage(self):
        try:
            self.flagimg.pack_forget()
        except:
            pass
        if self.country == '':
            self.countryimg = Image.open(os.path.join(os.path.dirname(__file__), "IMG/nlsn.png"))
        else:
            self.countryimg = Image.open(os.path.join(os.path.dirname(__file__), "IMG/{country}.png".format(country=self.country)))
        self.countryimg = self.countryimg.resize((30, 20), resample=Image.LANCZOS)
        self.countrytkimg = ImageTk.PhotoImage(self.countryimg)
        self.flagimg = tk.Label(self.CountryFrame, image=self.countrytkimg)
        self.flagimg.pack()#(x=0, y=0, relwidth=1, relheight=1)

    class go_button():
        def __init__(self, Frame, func, State):
            self.ico1 = Image.open(os.path.join(os.path.dirname(__file__), "IMG/play.png"))
            self.ico1 = self.ico1.resize((50, 50),resample=Image.LANCZOS)
            self.img1 = ImageTk.PhotoImage(self.ico1)
            self.ico2 = Image.open(os.path.join(os.path.dirname(__file__), "IMG/work.png"))
            self.ico2 = self.ico2.resize((50, 50),resample=Image.LANCZOS)
            self.img2 = ImageTk.PhotoImage(self.ico2)
            self.ico3 = Image.open(os.path.join(os.path.dirname(__file__), "IMG/done.png"))
            self.ico3 = self.ico3.resize((50, 50),resample=Image.LANCZOS)
            self.img3 = ImageTk.PhotoImage(self.ico3)
            self.ico4 = Image.open(os.path.join(os.path.dirname(__file__), "IMG/noo.png"))
            self.ico4 = self.ico4.resize((50, 50),resample=Image.LANCZOS)
            self.img4 = ImageTk.PhotoImage(self.ico4)
            self.ico5 = Image.open(os.path.join(os.path.dirname(__file__), "IMG/output.png"))
            self.ico5 = self.ico5.resize((49, 61),resample=Image.LANCZOS)
            self.img5 = ImageTk.PhotoImage(self.ico5)

            def go():
                self.Button.config(image=self.img2)
                State.set('Running...')
                self.Button.update()

                Log = pd.read_csv('TracebackLog.csv', sep=';')

                timestamp = str(datetime.datetime.today()).split(' ')
                date = timestamp[0].split('-')
                state, details, country, period = func()

                if state == 'Finished':
                    self.Button.config(image=self.img3)
                    State.set(state +' in ' + details)

                elif state == 'Finished with output':
                    self.Button.config(image=self.img5)
                    State.set(state + ' in ' + details)

                elif state == 'ERROR':
                    self.Button.config(image=self.img4)
                    State.set(state)

                showmessage(state, 'Program:  '+func.__name__[2:]+'\nCountry:   '+country+'\nWeek:       '+calc_week(period)+'\n'+details)

                Log.loc[len(Log.index) + 1] = [func.__name__[2:], date[0]+'-'+date[1]+'-'+date[2], timestamp[1][:8], country, period, state, details]
                Log.to_csv('TracebackLog.csv', sep=';', index=0)

            self.Button = tk.Button(Frame, command=lambda: go())
            self.Button.config(image=self.img1)
            self.Button['border'] = '0'

    class open_file_button:
        def __init__(self, Frame):
            self.ico = Image.open(os.path.join(os.path.dirname(__file__), "IMG/CSV.png"))
            self.ico = self.ico.resize((30, 30))
            self.img = ImageTk.PhotoImage(self.ico)

            self.Button = tk.Button(Frame, command=lambda: self.filepath())
            self.Button.config(image=self.img)

            self.FilePath = tk.StringVar()
            self.FilePath.set('Please choose file')
        def filepath(self):
            from tkinter import filedialog
            self.FilePath.set(filedialog.askopenfilename())

    class choose_dir_button:
        def __init__(self, Frame):
            self.ico = Image.open(os.path.join(os.path.dirname(__file__), "IMG/folder.png"))
            self.ico = self.ico.resize((30, 30))
            self.img = ImageTk.PhotoImage(self.ico)

            self.Button = tk.Button(Frame, command=lambda: self.dirpath())
            self.Button.config(image=self.img)

            self.DirPath = tk.StringVar()
            self.DirPath.set('Please choose directory')
        def dirpath(self):
            from tkinter import filedialog
            self.DirPath.set(filedialog.askdirectory())

    class save_file_button:
        def __init__(self, Frame, name, extension, func):
            self.ico = Image.open(os.path.join(os.path.dirname(__file__), r"IMG\xlsx.png"))
            self.ico = self.ico.resize((30, 30), resample=Image.LANCZOS)
            self.img = ImageTk.PhotoImage(self.ico)

            self.Button = tk.Button(Frame, text='Save!', command=lambda: self.savefile(name, extension, func))
            self.Button.config(image=self.img)

        def savefile(self, name, extension, func):
            from tkinter import filedialog
            try:
                self.DirPath = filedialog.asksaveasfilename(defaultextension=extension, initialfile=name)
                func(self.DirPath)
                showmessage('Saved', 'File ' + self.DirPath + ' saved successfully')
            except:
                pass

    class send_mail_button:
        def __init__(self, Frame, user, password, to, title, mail, dataframes, attachment, func):
            self.ico = Image.open(os.path.join(os.path.dirname(__file__), "IMG/mail.png"))
            self.ico = self.ico.resize((60, 43))
            self.img = ImageTk.PhotoImage(self.ico)

            self.Button = tk.Button(Frame, text='Send!', command=lambda: self.sendemail(user.get(), password.get(), to.get(), title.get(), mail.get(1.0,'end'), dataframes.get(), attachment.get(), func))
            self.Button.config(image=self.img)

        def savefile(self, func, attachment):
            func(attachment)
        def sendemail(self, user, password, to, title, mail, dataframes, attachment, func):
            # print('user: ', user)
            # print('password: ', password)
            # print('to: ', to)
            # print('title: ', title)
            # print('mail: ', mail)
            # print('dataframes: ', dataframes)
            # print('attachment: ', attachment)

            if attachment != '':
                attachment_check = os.path.isfile(attachment)
                if attachment_check == False:
                    self.savefile(func, attachment)

            try:
                sendmail(user, password, to, title, mail, dataframes, attachment=attachment)
            except Exception:
                import traceback
                traceback.print_exc()
                showmessage('ERROR', traceback.format_exc())

            if attachment != '':
                if attachment_check == False:
                    try:
                        os.remove(attachment)
                    except:
                        pass

    def choose_country(self, Frame):
        choose_window = Frame
        self.period = guess_period()
        self.country = ''
        self.countryimage()
        def on_country_change(*args):
            self.country = var_country.get()
            self.countryimage()
            self.country_specific()
        def on_period_change(*args):
            try:
                if var_period.get() != '':
                    self.period = int(entry_period.get())
            except:
                print(entry_period.get())
                showmessage('ERROR', 'Period has to be an integer')
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass
        def plus():
            self.period = self.period+1
            var_period.set(self.period)
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass
        def minus():
            self.period = self.period-1
            var_period.set(self.period)
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass

        var_country = tk.StringVar(choose_window)
        var_country.set('')
        var_country.trace('w', on_country_change)

        var_period = tk.StringVar(choose_window)
        var_period.set(guess_period())
        var_period.trace('w', on_period_change)
        var_week = tk.StringVar(choose_window)
        var_week.set(calc_week(int(var_period.get()))[:4]+' w'+calc_week(int(var_period.get()))[4:])

        Lbl_Period = tk.Label(choose_window, text='Period')
        Lbl_Country = tk.Label(choose_window, text='Country')
        entry_period = tk.Entry(choose_window, textvariable=var_period, width=7)
        week = tk.Label(choose_window, textvariable=var_week)
        but_plus = tk.Button(choose_window, text='+', width=2, command=lambda: plus())
        but_minus = tk.Button(choose_window, text='-', width=2, command=lambda: minus())
        entry_country = tk.OptionMenu(choose_window, var_country, 'DK', 'SE', 'NO')
        entry_country.configure(font=('Arial', 10))
        entry_country.config(width=12)

        Lbl_Period.grid(row=0, column=0, rowspan=2)
        entry_period.grid(row=0, column=1, rowspan=2)
        week.grid(row=0, column=2, rowspan=2, padx=10)
        but_plus.grid(row=0, column=3)
        but_minus.grid(row=1, column=3)
        Lbl_Country.grid(row=2, column=0)
        entry_country.grid(row=2, column=1, columnspan=2)

    def country_specific(self):
        if self.country == 'DK':
            if self.InfoBarText.get() == 'SQL queries' and (self.var_query.get() == 'SMR error flag check' or self.var_query.get() == 'MMS_STATUS check'):
                self.ButtL4L.grid(row=3, columnspan=2)
            elif self.InfoBarText.get() == 'Massive Update Stores':
                self.MUS2checkVar.set(0)
                self.MUS2files.grid_remove()
                self.MUS2lbl1.grid_remove()
                self.MUS2but1.Button.grid_remove()
                self.MUS2lbl2.grid_remove()
        elif self.country == 'SE':
            if self.InfoBarText.get() == 'SQL queries' and (self.var_query.get() == 'SMR error flag check' or self.var_query.get() == 'MMS_STATUS check'):
                self.CheckVarL4L.set(0)
                self.ButtL4L.grid_remove()
            elif self.InfoBarText.get() == 'Massive Update Stores':
                self.MUS2files.grid(row=0, column=1, sticky='w', padx=(5, 150))
                if self.MUS2checkVar.get() == 1:
                    self.MUS2lbl1.grid(row=3, column=0, sticky='e')
                    self.MUS2but1.Button.grid(row=3, column=1, columnspan=2, sticky='w', padx=(5, 100))
                    self.MUS2lbl2.grid(row=4, column=0, columnspan=2)
                elif self.MUS2checkVar.get() == 0:
                    self.MUS2lbl1.grid_remove()
                    self.MUS2but1.Button.grid_remove()
                    self.MUS2lbl2.grid_remove()
        elif self.country == 'NO':
            if self.InfoBarText.get() == 'SQL queries' and (self.var_query.get() == 'SMR error flag check' or self.var_query.get() == 'MMS_STATUS check'):
                self.CheckVarL4L.set(0)
                self.ButtL4L.grid_remove()
            elif self.InfoBarText.get() == 'Massive Update Stores':
                self.MUS2checkVar.set(0)
                self.MUS2files.grid_remove()
                self.MUS2lbl1.grid_remove()
                self.MUS2but1.Button.grid_remove()
                self.MUS2lbl2.grid_remove()

    def legacyacv(self):
        def goLegacyACV():
            import LegacyACV
            return LegacyACV.main(self.period, self.country, But1.FilePath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(master_file.dir_dictionary('madras', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR','Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Legacy ACV')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload Madras File')
        Lbl1.grid(row=1, column=0)

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacyacv())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goLegacyACV, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def legacycells(self):
        def goLegacyCells():
            import LegacyCells
            return LegacyCells.main(self.period, self.country, But1.FilePath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(
                    master_file.dir_dictionary('madras', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Legacy Cells')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload Madras File')
        Lbl1.grid(row=1, column=0)

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacycells())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goLegacyCells, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def mus(self):
        def goMUS():
            import MUS
            if self.MUS2checkVar.get() == 1:
                return MUS.main(self.period, self.country, But1.FilePath.get(), But2.DirPath.get(), path2=self.MUS2but1.FilePath.get())
            else:
                return MUS.main(self.period, self.country, But1.FilePath.get(), But2.DirPath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(master_file.dir_dictionary('shop_sample_census', self.country, calc_week(self.period)))
                try:
                    self.MUS2but1.FilePath.set(master_file.dir_dictionary('shop_sample_census2', self.country, calc_week(self.period)))
                except:
                    pass
                But2.DirPath.set(master_file.dir_dictionary('mus_output',self.country, calc_week(self.period)))
            except:
                showmessage('ERROR','Please set period and country correctly')
        def checkbox(Lbl11,But11,Lbl12):
            if self.MUS2checkVar.get() == 1:
                self.MUS2lbl1.grid(row=3, column=0, sticky='e')
                self.MUS2but1.Button.grid(row=3, column=1, columnspan=2, sticky='w', padx=(5,100))
                self.MUS2lbl2.grid(row=4, column=0, columnspan=2)
            elif self.MUS2checkVar.get() == 0:
                self.MUS2lbl1.grid_remove()
                self.MUS2but1.Button.grid_remove()
                self.MUS2lbl2.grid_remove()

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Massive Update Stores')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack(anchor='ne', fill='x')
        Frame2.grid_columnconfigure(0, weight=1)

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, sticky='e', pady=10)

        self.MUS2checkVar = tk.IntVar(value=0)
        self.MUS2files = tk.Checkbutton(Frame2, text='Load 2 files', variable=self.MUS2checkVar, command=lambda: checkbox(self.MUS2lbl1,self.MUS2but1,self.MUS2lbl2))
        # self.MUS2files.grid(row=0, column=1, sticky='w', padx=(5,150))
        fakeLbl = tk.Label(Frame2, text='                            ')
        fakeLbl.grid(row=1, column=1, sticky='w', padx=(5,150))

        Lbl1 = tk.Label(Frame2, text='Upload Shop_Sample_Census.csv')
        Lbl1.grid(row=1, column=0, sticky='e')

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1, sticky='w', padx=(5,150))

        Lbl2 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl2.grid(row=2, column=0, columnspan=2)

        self.MUS2lbl1 = tk.Label(Frame2, text='Upload second Shop_Sample_Census.csv')
        self.MUS2but1 = self.open_file_button(Frame2)
        self.MUS2lbl2 = tk.Label(Frame2, textvariable=self.MUS2but1.FilePath)

        Space1 = tk.Label(Frame2, height=2)
        Space1.grid(row=5)

        Lbl3 = tk.Label(Frame2, text='MUS Loader')
        Lbl3.grid(row=6, column=0, sticky='e')

        But2 = self.choose_dir_button(Frame2)
        But2.Button.grid(row=6, column=1, sticky='w', padx=(5,150))

        Lbl4 = tk.Label(Frame2, textvariable=But2.DirPath)
        Lbl4.grid(row=7, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: gomus())
        # GoButt = tk.Button(command=lambda: gomus())
        GoButt = self.go_button(self.MainFrame, goMUS, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def eforte(self):
        def goEforte():
            import Eforte
            return Eforte.main(self.period, self.country, But1.DirPath.get())
        def setstandardpaths():
            try:
                if calc_week(self.period)[:4] < calc_week(guess_period())[:4]:
                    But1.DirPath.set(master_file.dir_dictionary('eforte', self.country, calc_week(self.period))[:41] + calc_week(self.period)[:4] + '/' + str(calc_week(self.period)))
                else:
                    But1.DirPath.set(master_file.dir_dictionary('eforte', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR','Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Eforte')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Eforte reports folder')
        Lbl1.grid(row=1, column=0)

        But1 = self.choose_dir_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.DirPath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: goeforte())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goEforte, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def legacyMBDs(self):
        def goLegacyMBDs():
            import LegacyMBDs
            return LegacyMBDs.main(self.period, self.country, But1.FilePath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(
                    master_file.dir_dictionary('madras', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Legacy MBDs')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload Madras File')
        Lbl1.grid(row=1, column=0)

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacycells())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goLegacyMBDs, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def estimation_2(self):
        def goEstimation_2():
            import Estimation_2
            return Estimation_2.main(self.period, self.country, But1.FilePath.get())

        def setstandardpaths():
            try:
                But1.FilePath.set(
                    master_file.dir_dictionary('Estimation_2', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Estimation 2')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload Madras File')
        Lbl1.grid(row=1, column=0)

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacycells())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goEstimation_2, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def cellsdenmark(self):
        def goCellsDenmark():
            import Cells_Denmark
            return Cells_Denmark.main(self.period, self.country, But1.DirPath.get())
        def setstandardpaths():
            try:
                But1.DirPath.set(
                    master_file.dir_dictionary('Cells', self.country, calc_week(guess_period())))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Cells Denmark')
        self.country = 'DK'
        self.countryimage()

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Choose folder for Cells_Denmark file')
        Lbl1.grid(row=1, column=0)

        But1 = self.choose_dir_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.DirPath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        GoButt = self.go_button(self.MainFrame, goCellsDenmark, self.StateText)
        GoButt.Button.pack(side='bottom')

        # self.choose_country(Frame1)

    def hiidenmark(self):
        def goHierarchiesDenmark():
            import HiiDenmark
            return HiiDenmark.main(self.period, self.country, But1.FilePath.get(), But2.FilePath.get(), But3.DirPath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(master_file.dir_dictionary('MarketHierarchies_Denmark', self.country, calc_week(guess_period())))
                But2.FilePath.set(master_file.dir_dictionary('MBDs', self.country, calc_week(guess_period())))
                But3.DirPath.set(master_file.dir_dictionary('HierarchiesFolder', self.country, calc_week(guess_period())))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Hierarchies Denmark')
        self.country = 'DK'
        self.countryimage()

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload MarketHierarchies_Denmark.xlsx')
        Lbl1.grid(row=1, column=0)
        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)
        Lbl11 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl11.grid(row=2, column=0, columnspan=2)
        Space1 = tk.Label(Frame2, height=2)
        Space1.grid(row=3)

        Lbl2 = tk.Label(Frame2, text='Upload MBDs.xlsx')
        Lbl2.grid(row=4, column=0)
        But2 = self.open_file_button(Frame2)
        But2.Button.grid(row=4, column=1)
        Lbl22 = tk.Label(Frame2, textvariable=But2.FilePath)
        Lbl22.grid(row=5, column=0, columnspan=2)
        Space2 = tk.Label(Frame2, height=2)
        Space2.grid(row=6)

        Lbl3 = tk.Label(Frame2, text='Choose output folder')
        Lbl3.grid(row=7, column=0)
        But3 = self.choose_dir_button(Frame2)
        But3.Button.grid(row=7, column=1)
        Lbl33 = tk.Label(Frame2, textvariable=But3.DirPath)
        Lbl33.grid(row=8, column=0, columnspan=2)

        GoButt = self.go_button(self.MainFrame, goHierarchiesDenmark, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def kpi_cssi(self):
        def goKPI_CSSI():
            import KPI_CSSI
            return KPI_CSSI.main(self.period, self.country, But1.FilePath.get())
        def setstandardpaths():
            try:
                But1.FilePath.set(master_file.dir_dictionary('kpi_cssi', self.country, calc_week(self.period)))
            except:
                showmessage('ERROR','Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('KPI for CSSI')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload StoreDir File')
        Lbl1.grid(row=1, column=0)

        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacyacv())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goKPI_CSSI, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def causal_sample_selection(self):
        def goCausal_Sample_Selection():
            area_list=[]
            for area in areas.keys():
                if areas[area].get() == 1:
                    area_list.append(area)
            print(self.period, var_banner.get().split(' ')[0], area_list, But1.FilePath.get(), But2.FilePath.get(), But3.DirPath.get())

            import Causal_sample_selection
            return Causal_sample_selection.main(self.period, int(var_banner.get().split(' ')[0]), area_list, But1.FilePath.get(), But2.FilePath.get(), But3.DirPath.get())#, self.country)
        def setstandardpaths():
            try:
                But1.FilePath.set(master_file.dir_dictionary('storedir_current', self.country, calc_week(guess_period())))
                But2.FilePath.set(master_file.dir_dictionary('causal_sample', self.country, calc_week(guess_period())))
                But3.DirPath.set(master_file.dir_dictionary('SampleSelectionFolder', self.country, calc_week(guess_period())))
            except:
                showmessage('ERROR', 'Please set period and country correctly')

        # class favorites_button:
        #     def __init__(self, Frame, entry):
        #         self.ico = Image.open(os.path.join(os.path.dirname(__file__), "IMG/area.png"))
        #         self.ico = self.ico.resize((34, 34))
        #         self.img = ImageTk.PhotoImage(self.ico)
        #
        #         self.Button = tk.Button(Frame, command=lambda: self.set_favourites(entry))
        #         self.Button.config(image=self.img)
        #
        #     def set_favourites(self, entry):
        #         self.favtop = tk.Toplevel(height=280, width=250)
        #         self.favtop.title(' Add mails')
        #         self.favtop.pack_propagate(0)
        #
        #
        #         # 1 HOVEDSTAD
        #         # 2 OVRIGE SJAELLAND
        #         # 3 FYN
        #         # 4 SYDDANMARK EX FYN
        #         # 5 MIDTJYLLAND
        #         # 6 NORDJYLLAND
        #
        #
        #         self.HOVEDSTADvar = tk.IntVar(value=0)
        #         self.OVRIGE_SJAELLANDvar = tk.IntVar(value=0)
        #         self.FYNvar = tk.IntVar(value=0)
        #         self.SYDDANMARK_EX_FYNvar = tk.IntVar(value=0)
        #         self.MIDTJYLLANDvar = tk.IntVar(value=0)
        #         self.NORDJYLLANDvar = tk.IntVar(value=0)
        #
        #         favourites = {'HOVEDSTAD': self.HOVEDSTADvar,
        #                       'OVRIGE SJAELLAND': self.OVRIGE_SJAELLANDvar,
        #                       'FYN': self.FYNvar,
        #                       'SYDDANMARK EX FYN': self.SYDDANMARK_EX_FYNvar,
        #                       'MIDTJYLLAND': self.MIDTJYLLANDvar,
        #                       'NORDJYLLAND': self.NORDJYLLANDvar,
        #                       }
        #
        #         mail_to = entry.get().replace(' ', '').split(',')
        #         for mail in mail_to:
        #             if mail in favourites.keys():
        #                 favourites[mail].set(1)
        #
        #         HOVEDSTADBut = tk.Checkbutton(self.favtop, text='HOVEDSTAD', variable=self.HOVEDSTADvar)
        #         OVRIGE_SJAELLANDBut = tk.Checkbutton(self.favtop, text='OVRIGE SJAELLAND', variable=self.OVRIGE_SJAELLANDvar)
        #         FYNBut = tk.Checkbutton(self.favtop, text='FYN', variable=self.FYNvar)
        #         SYDDANMARK_EX_FYNBut = tk.Checkbutton(self.favtop, text='SYDDANMARK EX FYN', variable=self.SYDDANMARK_EX_FYNvar)
        #         MIDTJYLLANDBut = tk.Checkbutton(self.favtop, text='MIDTJYLLAND', variable=self.MIDTJYLLANDvar)
        #         NORDJYLLANDBut = tk.Checkbutton(self.favtop, text='NORDJYLLAND', variable=self.NORDJYLLANDvar)
        #
        #         HOVEDSTADBut.pack(side='top', anchor='w', padx=(10, 0))
        #         OVRIGE_SJAELLANDBut.pack(side='top', anchor='w', padx=(10, 0))
        #         FYNBut.pack(side='top', anchor='w', padx=(10, 0))
        #         SYDDANMARK_EX_FYNBut.pack(side='top', anchor='w', padx=(10, 0))
        #         MIDTJYLLANDBut.pack(side='top', anchor='w', padx=(10, 0))
        #         NORDJYLLANDBut.pack(side='top', anchor='w', padx=(10, 0))
        #
        #         ApplyBut = self.add_button(self.favtop, entry, favourites)
        #         ApplyBut.Button.pack(side='bottom')
        #
        #     class add_button:
        #         def __init__(self, Frame, entry, favourites):
        #             self.ico = Image.open(os.path.join(os.path.dirname(__file__), r"IMG\add.png"))
        #             self.ico = self.ico.resize((40, 40), resample=Image.LANCZOS)
        #             self.img = ImageTk.PhotoImage(self.ico)
        #
        #             self.Button = tk.Button(Frame, text='add!', command=lambda: self.add(Frame, entry, favourites))
        #             self.Button.config(image=self.img)
        #         def add(self, frame, entry, favourites):
        #             if entry.get() == 'use "," as separator | e.g. aaa@nielsen.com, bbb@gmail.com':
        #                 entry.set('')
        #             mail_to = entry.get().replace(' ', '').split(',')
        #             new_mail_to = ''
        #             for mail in mail_to:
        #                 if mail not in favourites.keys() and mail_to[0] != '':
        #                     new_mail_to += mail + ', '
        #                 elif mail in favourites.keys() and favourites[mail].get() == 1:
        #                     new_mail_to += mail + ', '
        #             for mail in favourites.keys():
        #                 if favourites[mail].get() == 1 and mail not in new_mail_to.replace(' ','').split(','):
        #                     new_mail_to += mail + ', '
        #             entry.set(new_mail_to[:-2])
        #             frame.destroy()

        self.country = 'DK'
        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Causal sample selection')

        # Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        # Frame1.pack_propagate(0)
        # Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()


        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Upload storedir file')
        Lbl1.grid(row=1, column=0)
        But1 = self.open_file_button(Frame2)
        But1.Button.grid(row=1, column=1)
        Lbl11 = tk.Label(Frame2, textvariable=But1.FilePath)
        Lbl11.grid(row=2, column=0, columnspan=2)
        # Space1 = tk.Label(Frame2, height=2)
        # Space1.grid(row=3)

        Lbl2 = tk.Label(Frame2, text='Upload causal sample file.xlsx')
        Lbl2.grid(row=4, column=0)
        But2 = self.open_file_button(Frame2)
        But2.Button.grid(row=4, column=1)
        Lbl22 = tk.Label(Frame2, textvariable=But2.FilePath)
        Lbl22.grid(row=5, column=0, columnspan=2)
        # Space2 = tk.Label(Frame2, height=2)
        # Space2.grid(row=6)

        Lbl3 = tk.Label(Frame2, text='Choose output folder')
        Lbl3.grid(row=7, column=0)
        But3 = self.choose_dir_button(Frame2)
        But3.Button.grid(row=7, column=1)
        Lbl33 = tk.Label(Frame2, textvariable=But3.DirPath)
        Lbl33.grid(row=8, column=0, columnspan=2)

        Space1 = tk.Label(Frame2)
        Space1.grid(row=9)
        Lbl1 = tk.Label(Frame2, text='Select BANNER:')
        var_banner = tk.StringVar(value='0 - ALL')
        entry_banner = tk.OptionMenu(Frame2, var_banner,
                                     '0 - ALL',
                                     '4 - 7-ELEVEN CITY',
                                     '5 - NAERKOB',
                                     '6 - 7-ELEVEN GASOLINE',
                                     '10 - LETKOB',
                                     '20 - KVICKLY XTRA',
                                     '30 - KVICKLY',
                                     '40 - DAGLIBRUGSEN',
                                     '50 - SUPERBRUGSEN',
                                     '70 - MAD COOPERATIVET',
                                     '90 - BRUGSEN',
                                     '100 - FAKTA',
                                     '110 - IRMA',
                                     '121 - FOTEX FOOD CONV.',
                                     '122 - BILKA',
                                     '123 - FOTEX',
                                     '124 - SALLING',
                                     '125 - NETTO',
                                     '126 - A-Z',
                                     '127 - DOGNNETTO',
                                     '140 - ALDI',
                                     '150 - LIDL',
                                     '181 - Q8 CENTRAL',
                                     '182 - BFI EXTRA',
                                     '184 - CIRCLE K NON-CHAIN',
                                     '185 - BFI SHELL RBA',
                                     '190 - MATAS',
                                     '233 - REMA 1000',
                                     '252 - ABC LAVPRIS',
                                     '271 - 7-ELEVEN TRAIN',
                                     '281 - Q8 DECENTRAL',
                                     '284 - CIRCLE K SHELL',
                                     '285 - SHELL KAEDE',
                                     '286 - OK PLUS',
                                     '305 - LOVBJERG',
                                     '317 - OVRIGE EDEKA',
                                     '350 - MENY',
                                     '379 - SUPERBEST',
                                     '384 - CIRCLE K CHAIN',
                                     '385 - BFI SHELL DO',
                                     '411 - KIWI',
                                     '421 - SPAR',
                                     '422 - EURO SPAR',
                                     '423 - Super Spar',
                                     '430 - MIN KOBMAND',
                                     '437 - KWIK SPAR',
                                     '451 - OVRIGE SUPERGROS',
                                     '699 - OVRIGE',
                                     '910 - COOP DK MAD',
                                     '922 - BILKA ONLINE',
                                     '923 - FOTEX ONLINE',
                                     '924 - SALLING ONLINE',
                                     '930 - COOP DK SHOPPING')
        Lbl1.grid(row=11, column=0, columnspan=2)
        entry_banner.grid(row=12, column=0, columnspan=2)

        Space2 = tk.Label(Frame2)
        Space2.grid(row=13)
        Lbl2 = tk.Label(Frame2, text='Select AREA:')
        Lbl2.grid(row=14, column=0, columnspan=2)

        HOVEDSTADvar = tk.IntVar(value=0)
        OVRIGE_SJAELLANDvar = tk.IntVar(value=0)
        FYNvar = tk.IntVar(value=0)
        SYDDANMARK_EX_FYNvar = tk.IntVar(value=0)
        MIDTJYLLANDvar = tk.IntVar(value=0)
        NORDJYLLANDvar = tk.IntVar(value=0)

        areas = {1: HOVEDSTADvar,
                  2: OVRIGE_SJAELLANDvar,
                  3: FYNvar,
                  4: SYDDANMARK_EX_FYNvar,
                  5: MIDTJYLLANDvar,
                  6: NORDJYLLANDvar,
                  }

        HOVEDSTADBut = tk.Checkbutton(Frame2, text='1-HOVEDSTAD', variable=HOVEDSTADvar)
        OVRIGE_SJAELLANDBut = tk.Checkbutton(Frame2, text='2-OVRIGE SJAELLAND', variable=OVRIGE_SJAELLANDvar)
        FYNBut = tk.Checkbutton(Frame2, text='3-FYN', variable=FYNvar)
        SYDDANMARK_EX_FYNBut = tk.Checkbutton(Frame2, text='4-SYDDANMARK EX FYN', variable=SYDDANMARK_EX_FYNvar)
        MIDTJYLLANDBut = tk.Checkbutton(Frame2, text='5-MIDTJYLLAND', variable=MIDTJYLLANDvar)
        NORDJYLLANDBut = tk.Checkbutton(Frame2, text='6-NORDJYLLAND', variable=NORDJYLLANDvar)

        HOVEDSTADBut.grid(row=15, column=0, sticky='w', padx=(38,0))
        OVRIGE_SJAELLANDBut.grid(row=16, column=0, sticky='w', padx=(38,0))
        FYNBut.grid(row=17, column=0, sticky='w', padx=(38,0))
        SYDDANMARK_EX_FYNBut.grid(row=15, column=1, sticky='w', padx=(38,0))
        MIDTJYLLANDBut.grid(row=16, column=1, sticky='w', padx=(38,0))
        NORDJYLLANDBut.grid(row=17, column=1, sticky='w', padx=(38,0))


        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacyacv())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goCausal_Sample_Selection, self.StateText)
        GoButt.Button.pack(side='bottom')

        # self.choose_country(Frame1)

    def drutynacausala(self):
        def goDrutyCausal():
            import CausalCellWire
            return CausalCellWire.main(self.country, self.period, But1.DirPath.get())
        def setstandardpaths():
            try:
                But1.DirPath.set(r'E:\Shared drives\Stat Ops Nordic\{country}\C19\{year}_{week}'.format(country=self.country, year=calc_week(self.period)[:4], week=calc_week(self.period)[4:]))
            except:
                showmessage('ERROR','Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Causal cell industry after CSU')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Choose output folder')
        Lbl1.grid(row=1, column=0)

        But1 = self.choose_dir_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.DirPath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacyacv())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goDrutyCausal, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def drutynanoncensusa(self):
        def goDrutyCausal():
            import NonCensusCellWire
            return NonCensusCellWire.main(self.country, self.period, But1.DirPath.get())
        def setstandardpaths():
            try:
                But1.DirPath.set(r'E:\Shared drives\Stat Ops Nordic\{country}\C19\{year}_{week}'.format(country=self.country, year=calc_week(self.period)[:4], week=calc_week(self.period)[4:]))
            except:
                showmessage('ERROR','Please set period and country correctly')

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('NonCensus cell industry after SI')

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        SetButt = tk.Button(Frame2, text='Set standard paths', command=lambda: setstandardpaths())
        SetButt.grid(row=0, column=0, columnspan=2, pady=10)

        Lbl1 = tk.Label(Frame2, text='Choose output folder')
        Lbl1.grid(row=1, column=0)

        But1 = self.choose_dir_button(Frame2)
        But1.Button.grid(row=1, column=1)

        Lbl4 = tk.Label(Frame2, textvariable=But1.DirPath)
        Lbl4.grid(row=2, column=0, columnspan=2)

        # GoButt = tk.Button(self.MainFrame, text='Go!', command=lambda: golegacyacv())
        # GoButt.pack(side='bottom')
        GoButt = self.go_button(self.MainFrame, goDrutyCausal, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

    def tracebacklog(self):
        def show_filters(Frame):
            if self.show_filter == True:
                self.show_filter = False
                Frame.pack_forget()
            elif self.show_filter == False:
                self.show_filter = True
                Frame.pack(side='top')
        def on_country_change(*args):
            self.filter_country = var_country.get()
        def on_year_change(*args):
            self.filter_year = var_year.get()
            self.filter_date = self.filter_year+'-'+self.filter_month+'-'+self.filter_day
        def on_month_change(*args):
            self.filter_month = var_month.get()
            self.filter_date = self.filter_year+'-'+self.filter_month+'-'+self.filter_day
        def on_day_change(*args):
            self.filter_day = var_day.get()
            self.filter_date = self.filter_year+'-'+self.filter_month+'-'+self.filter_day
        def on_period_change(*args):
            try:
                if var_period.get() != '' and var_period.get() != '-':
                    self.filter_period = int(entry_period.get())
            except:
                print(entry_period.get())
                showmessage('ERROR', 'Period has to be an integer')
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass
        def on_state_change(*args):
            self.filter_state = var_state.get()
        def on_program_change(*args):
            self.filter_program = var_program.get()
        def plus():
            try:
                self.filter_period = self.filter_period+1
                var_period.set(self.filter_period)
            except:
                self.filter_period = guess_period() + 1
                var_period.set(self.filter_period)
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass
        def minus():
            try:
                self.filter_period = self.filter_period-1
                var_period.set(self.filter_period)
            except:
                self.filter_period = guess_period() - 1
                var_period.set(self.filter_period)
            try:
                var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
            except:
                pass
        def set_today():
            var_year.set(str(datetime.datetime.today()).split(' ')[0].split('-')[0])
            var_month.set(str(datetime.datetime.today()).split(' ')[0].split('-')[1])
            var_day.set(str(datetime.datetime.today()).split(' ')[0].split('-')[2])
        def reset_date():
            var_year.set('-')
            var_month.set('-')
            var_day.set('-')
        def reset_all():
            self.filter_country = '-'
            var_country.set('-')
            self.filter_period = '-'
            var_period.set('-')
            self.filter_date = '-.-.-'
            self.filter_year = 'YYYY'
            var_year.set('YYYY')
            self.filter_month = 'MM'
            var_month.set('MM')
            self.filter_day = 'DD'
            var_day.set('DD')
            self.filter_state = '-'
            var_state.set('-')
            var_program.set('-')
            var_week.set('-')
        def gofilter(Frame):
            for widget in Frame.winfo_children():
                widget.destroy()

            show_button = tk.Button(Frame2, text='Show/Hide Filters', bd=3, relief='ridge', overrelief='groove',
                                    command=lambda: show_filters(Frame1))
            show_button.pack(fill='x')

            Log = pd.read_csv('TracebackLog.csv', sep=';')
            Log = Log.drop(Log[Log.State == 'ERROR'].index)
            Log_err = pd.read_csv('TracebackLog.csv', sep=';')
            Log_err = Log_err.drop(Log[Log.State != 'ERROR'].index)
            Log_err = Log_err.drop(['Details'], axis=1)
            Log = pd.concat([Log, Log_err], sort=0)
            Log = Log.sort_values(['Date', 'Time'], ascending=[0, 0])

            print(self.filter_period)
            print(self.filter_country)
            print(self.filter_date)
            print(self.filter_state)
            print(self.filter_program)

            if self.filter_country != '-':
                print('country filter applied')
                Log = Log.drop(Log[Log.Country != self.filter_country].index)
            if self.filter_period != '' and self.filter_period != '-':
                print('period filter applied')
                Log = Log.drop(Log[Log.Period != self.filter_period].index)
            if self.filter_date != 'YYYY-MM-DD':
                print('date filter applied')
                Log = Log.drop(Log[Log.Date != self.filter_date].index)
            if self.filter_state != '-':
                print('state filter applied')
                Log = Log.drop(Log[Log.State != self.filter_state].index)
            if self.filter_program != '-':
                print('program filter applied')
                Log = Log.drop(Log[Log.Program != self.filter_program].index)

            showtable(Frame, ('', Log))

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('Traceback Log')
        self.country = ''
        self.countryimage()

        self.ico_filter = Image.open(os.path.join(os.path.dirname(__file__), "IMG/filter.png"))
        self.ico_filter = self.ico_filter.resize((50, 50), resample=Image.LANCZOS)
        self.img_filter = ImageTk.PhotoImage(self.ico_filter)

        Log = pd.read_csv('TracebackLog.csv', sep=';')
        Log = Log.drop(Log[Log.State == 'ERROR'].index)
        Log_err = pd.read_csv('TracebackLog.csv', sep=';')
        Log_err = Log_err.drop(Log[Log.State != 'ERROR'].index)
        Log_err = Log_err.drop(['Details'], axis=1)
        Log = pd.concat([Log,Log_err], sort=0)
        Log = Log.sort_values(['Date', 'Time'], ascending=[0, 0])

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack_propagate(0)
        Frame2.pack(fill='both', expand=1, side='bottom')
        show_button = tk.Button(Frame2, text='Show/Hide Filters', bd=3, relief='ridge', overrelief='groove',
                                command=lambda: show_filters(Frame1))
        show_button.pack(fill='x')
        showtable(Frame2, ('', Log))

        var_country = tk.StringVar(Frame1)
        var_country.set('-')
        var_country.trace('w', on_country_change)

        var_period = tk.StringVar(Frame1)
        var_period.set('-')
        var_period.trace('w', on_period_change)
        var_week = tk.StringVar(Frame1)
        try:
            var_week.set(calc_week(int(var_period.get()))[:4] + ' w' + calc_week(int(var_period.get()))[4:])
        except:
            var_week.set(var_period.get())

        var_year = tk.StringVar(Frame1)
        var_year.set('YYYY')
        var_year.trace('w', on_year_change)
        var_month = tk.StringVar(Frame1)
        var_month.set('MM')
        var_month.trace('w', on_month_change)
        var_day = tk.StringVar(Frame1)
        var_day.set('DD')
        var_day.trace('w', on_day_change)
        var_state = tk.StringVar(Frame1)
        var_state.set('-')
        var_state.trace('w', on_state_change)
        var_program = tk.StringVar(Frame1)
        var_program.set('-')
        var_program.trace('w', on_program_change)

        Lbl_Period = tk.Label(Frame1, text='Period')
        Lbl_Country = tk.Label(Frame1, text='Country')
        entry_period = tk.Entry(Frame1, textvariable=var_period, width=7)
        week = tk.Label(Frame1, textvariable=var_week)
        but_plus = tk.Button(Frame1, text='+', width=2, command=lambda: plus())
        but_minus = tk.Button(Frame1, text='-', width=2, command=lambda: minus())
        entry_country = tk.OptionMenu(Frame1, var_country, '-','DK','SE','NO')
        entry_country.configure(font=('Arial', 10))
        entry_country.config(width=12)

        FilterButton = tk.Button(Frame1, text='filter', command=lambda: gofilter(Frame2))
        FilterButton.config(image=self.img_filter)
        ResetAllButton = tk.Button(Frame1, text='Restet all', command=lambda: reset_all())

        Lbl_Date = tk.Label(Frame1, text='Date')
        entry_year = tk.OptionMenu(Frame1, var_year, 'YYYY','2019','2020','2021','2022')
        entry_year.configure(font=('Arial', 10))
        entry_year.config(width=5)
        entry_month = tk.OptionMenu(Frame1, var_month, 'MM','01','02','03','04','05','06','07','08','09','10','11','12')
        entry_month.configure(font=('Arial', 10))
        entry_month.config(width=3)
        entry_day = tk.OptionMenu(Frame1, var_day, 'DD','01','02','03','04','05','06','07','08','09',
                                  '10','11','12','13','14','15','16','17','18','19',
                                  '20','21','22','23','24','25','26','27','28','29','30','31')
        entry_day.configure(font=('Arial', 10))
        entry_day.config(width=3)
        but_today = tk.Button(Frame1, text='Today', command=lambda: set_today())
        but_today.config(width=7)
        but_reset_date = tk.Button(Frame1, text='Reset', command=lambda: reset_date())
        but_reset_date.config(width=7)

        Lbl_State = tk.Label(Frame1, text='Program/State')
        entry_state = tk.OptionMenu(Frame1, var_state, '-', *Log.State.unique())
        entry_program = tk.OptionMenu(Frame1, var_program, '-', *Log.Program.unique())

        Lbl_Period.grid(row=0, column=0, rowspan=2)
        entry_period.grid(row=0, column=1, rowspan=2)
        week.grid(row=0, column=2, rowspan=2, padx=10)
        but_plus.grid(row=0, column=3)
        but_minus.grid(row=1, column=3)
        Lbl_Country.grid(row=2, column=0)
        entry_country.grid(row=2, column=1, columnspan=2)
        FilterButton.grid(row=0, column=4, rowspan=2, padx=15)
        ResetAllButton.grid(row=2, column=4)
        Lbl_Date.grid(row=0, column=5)
        entry_year.grid(row=1, column=5)
        entry_month.grid(row=1, column=6)
        entry_day.grid(row=1, column=7)
        but_today.grid(row=0, column=6)
        but_reset_date.grid(row=0, column=7)
        Lbl_State.grid(row=2, column=5)
        entry_program.grid(row=2, column=6)
        entry_state.grid(row=2, column=7)

    def SQL_queries(self):
        def goSQL_queries():
            import SQL_fav
            if self.var_query.get() == 'SMR error flag check':
                if self.country != 'DK':
                    self.CheckVarL4L.set(0)
                return SQL_fav.SMR(self.period, self.country, self.CheckVarL4L.get())
            elif self.var_query.get() == 'MMS_STATUS check':
                if self.country != 'DK':
                    self.CheckVarL4L.set(0)
                return SQL_fav.MSR(self.period, self.country, self.CheckVarL4L.get())
            elif self.var_query.get() == 'Changes in cell_content':
                return SQL_fav.CELL_CONTENT(self.period, self.country, var_cel_id.get())
            elif self.var_query.get() == 'sho_id -> sho_external_code':
                return SQL_fav.SHO_EX(self.period, self.country, entry_shops.get(1.0, 'end'))
            elif self.var_query.get() == 'sho_external_code -> sho_id':
                return SQL_fav.SHO_ID(self.period, self.country, entry_shops.get(1.0, 'end'))
            else:
                return 'ERROR', 'wrong period/country', self.country, self.period
        def on_query_change(*args):
            if self.var_query.get() == 'SMR error flag check':
                hide_all()
                self.CheckVarL4L.set(0)
                if self.country == 'DK':
                    self.ButtL4L.grid(row=3, columnspan=2)
            elif self.var_query.get() == 'MMS_STATUS check':
                hide_all()
                self.CheckVarL4L.set(0)
                if self.country == 'DK':
                    self.ButtL4L.grid(row=3, columnspan=2)
            elif self.var_query.get() == 'Changes in cell_content':
                hide_all()
                Lbl1.grid(row=3, column=0, sticky='e')
                entry_cel_id.grid(row=3, column=1, sticky='w')
            elif self.var_query.get() == 'sho_id -> sho_external_code':
                hide_all()
                Lbl2.grid(row=3, columnspan=2)
                entry_shops.grid(row=4, columnspan=2)
            elif self.var_query.get() == 'sho_external_code -> sho_id':
                hide_all()
                Lbl3.grid(row=3, columnspan=2)
                entry_shops.grid(row=4, columnspan=2)
            else:
                hide_all()
        def hide_all():
            self.ButtL4L.grid_remove()
            Lbl1.grid_remove()
            entry_cel_id.grid_remove()
            Lbl2.grid_remove()
            Lbl3.grid_remove()
            entry_shops.grid_remove()

        self.MainFrame.destroy()
        self.mainframe()
        self.InfoBarText.set('SQL queries')
        self.country = ''
        self.countryimage()

        Frame1 = tk.Frame(self.MainFrame, bd=1, relief='groove')
        Frame1.pack_propagate(0)
        Frame1.pack(side='top')

        Frame2 = tk.Frame(self.MainFrame)
        Frame2.pack()

        Space1 = tk.Label(Frame2)

        self.var_query = tk.StringVar(Frame2)
        self.var_query.set('Choose query to run:')
        self.var_query.trace('w', on_query_change)
        entry_query = tk.OptionMenu(Frame2, self.var_query,
                                    'sho_id -> sho_external_code',
                                    'sho_external_code -> sho_id',
                                    'SMR error flag check',
                                    'MMS_STATUS check',
                                    'Changes in cell_content'
                                    )
        entry_query.configure(font=('Arial', 10))
        entry_query.config(width=22)

        Space2 = tk.Label(Frame2)

        self.CheckVarL4L = tk.IntVar(value=0)
        self.ButtL4L = tk.Checkbutton(Frame2, text='L4L', variable=self.CheckVarL4L)

        Lbl1 = tk.Label(Frame2, text='CEL_ID: ')
        var_cel_id = tk.StringVar(Frame2)
        var_cel_id.set('')
        entry_cel_id = tk.Entry(Frame2, textvariable=var_cel_id, width=10)

        Lbl2 = tk.Label(Frame2, text="Sho_id's: ")
        Lbl3 = tk.Label(Frame2, text="Sho_external_code's: ")
        from tkinter import scrolledtext as scrtxt
        entry_shops = scrtxt.ScrolledText(Frame2, width=45, height=6)
        entry_shops.insert('insert', 'Please use coma "," as separator')

        Space1.grid(row=0, columnspan=2)
        entry_query.grid(row=1, columnspan=2)
        Space2.grid(row=2, columnspan=2)

        GoButt = self.go_button(self.MainFrame, goSQL_queries, self.StateText)
        GoButt.Button.pack(side='bottom')

        self.choose_country(Frame1)

if __name__ == '__main__':
    window('SOprog')