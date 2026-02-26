import customtkinter as ctk
import os
import webbrowser
from CTkMessagebox import CTkMessagebox
from survey_analyzer import SurveyAnalyzer
from CTkToolTip import *

class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        # Basic configuration
        self.title('HGSFP Survey Tool')
        self.resizable(False,False)
        #self.grid_rowconfigure(0, weight=1)  
        #self.grid_columnconfigure(0, weight=1)
        # customtkinter variables
        self.input_path = ctk.StringVar(self, value='No input path specified')
        self.summary = ctk.BooleanVar(self, value=False)
        self.output_path = ctk.StringVar(self, value='No output path specified')
        self.filepaths = {}
        #self.geometry('1080x720')
        # Explanatory text
        self.explanatory_frame = ctk.CTkFrame(self)
        self.explanatory_frame.pack(padx=5,pady=(5,2.5),fill='both') #grid(row=0,column=0,padx=10,pady=(5,5),sticky='nwe')
        self.explanatory_label = ctk.CTkLabel(self.explanatory_frame,text='Welcome to the HGSFP Survey Tool! This tool automates the analysis and PDF creation of the survey results.\n' \
        'The workflow is as follows:\n' \
        '\t 1. Choose the input JSON file containing the survey data.\n' \
        '\t 2. Choose the folder where the PDFs will be saved to.\n' \
        '\t 3. Enter the name of the industry lecture.\n' \
        '\t 4. Decide whether or not to group similar comments regarding the organization or topics.\n' \
        '\t 5. Perform the analysis.\n' \
        'Optional: Use the dropdown menu at the bottom to open the PDF files directly from this programme.',justify='left')
        self.explanatory_label.grid(row=0,column=0,padx=10,pady=(5,5))
        # Configure a drop-in read file
        self.input_output_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_output_frame.pack(padx=5,pady=(2.5,2.5),fill='both')#grid(row=1,column=0,padx=10,pady=(5,5),sticky='nwe')
        self.label_input_path = ctk.CTkLabel(self.input_output_frame,text=self.input_path.get())
        self.label_output_path = ctk.CTkLabel(self.input_output_frame,text=self.output_path.get())
        self.jsonbutton = ctk.CTkButton(self.input_output_frame,text='Select input file',command=self.SetInputPath)
        self.jsonbutton.grid(row=0,column=0,padx=10,pady=(5,5),sticky='w')
        self.savebutton = ctk.CTkButton(self.input_output_frame,text='Select output path',command=self.SetOutputPath)
        self.savebutton.grid(row=1,column=0,padx=10,pady=(5,5),sticky='w')
        self.label_input_path.grid(row=0,column=1,padx=10,pady=(5,5),sticky='w')
        self.label_output_path.grid(row=1,column=1,padx=10,pady=(5,5),sticky='w')
        # Checkbox for summary of suggestion/topic comments
        self.il_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.il_frame.pack(padx=5,pady=(2.5,2.5),fill='both')
        self.il_frame.grid_columnconfigure(1, weight=1)
        self.il_label = ctk.CTkLabel(self.il_frame, text='Enter industry lecture title: ')
        self.il_input_box = ctk.CTkEntry(self.il_frame)
        self.il_label.grid(row=0,column=0,padx=10,pady=(5,5),sticky='w')
        self.il_input_box.grid(row=0,column=1,padx=5,pady=(5,5),sticky='ew')
        self.checkbox_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_frame.pack(padx=5,pady=(2.5,2.5),fill='both')
        self.checkbox_frame.grid_columnconfigure(2, weight=1)
        self.checkbox = ctk.CTkCheckBox(
            self.checkbox_frame,
            text='Summarize comments',
            variable=self.summary,
            onvalue=True,
            offvalue=False,
        )
        self.info_icon = ctk.CTkLabel(self.checkbox_frame, text="❓", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray", cursor="question_arrow")
        self.tooltip_summarize = CTkToolTip(self.info_icon,delay=0.5,message="The comments are summarized using a so-called sentence transformer, grouping sentences by their meaning.\n" \
        "Sentence transformers can make mistakes, so better check the raw file!\n"\
        "For further information visit: https://sbert.net/")
        self.perform_analysis = ctk.CTkButton(self.checkbox_frame,text='Perform analysis!',command=self.DoAnalysis)
        self.checkbox.grid(row=0,column=0,padx=(10,1),pady=(5,5),sticky='w')
        self.info_icon.grid(row=0, column=1, padx=1,sticky='w')
        self.perform_analysis.grid(row=0,column=3,padx=10,pady=(5,5),sticky='e')
        # Footer row: PDF dropdown + About button
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(padx=5, pady=(2.5, 5), fill='both')
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.dropdown = ctk.CTkComboBox(self.footer_frame, command=self.OpenFile)
        self.dropdown.set('Choose a PDF to show')
        self.dropdown.configure(values=[])
        self.dropdown.grid(row=0, column=0, padx=(10, 5), pady=(5, 5), sticky='ew')

        self.about_icon = ctk.CTkButton(
            self.footer_frame,
            text='About',
            font=ctk.CTkFont(size=12, weight='bold'),
            text_color='gray',
            cursor='question_arrow',
            command=self.OpenAboutWindow,
            width=80,
        )
        self.about_icon.grid(row=0, column=1, padx=(5, 10), pady=(5, 5), sticky='e')


    def OpenAboutWindow(self):
        # Erstelle ein neues Fenster
        about_win = ctk.CTkToplevel(self)
        about_win.title("About this app")
        about_win.minsize(320, 220)

        # Verhindert, dass das Hauptfenster bedient werden kann (optional)
        about_win.grab_set()

        # Inhalt hinzufuegen
        title_label = ctk.CTkLabel(about_win, text="HGSFP Survey Tool", font=("Arial", 16, "bold"))
        title_label.pack(padx=10, pady=6, anchor="w")

        details_frame = ctk.CTkFrame(about_win, fg_color="transparent")
        details_frame.pack(padx=10, pady=1)

        created_label = ctk.CTkLabel(details_frame, text="Created by: Hagen-Wolfgang Buehler")
        created_label.pack(pady=1, anchor="w")

        version_label = ctk.CTkLabel(details_frame, text="Version: 1.0.0")
        version_label.pack(pady=1, anchor="w")

        contact_row = ctk.CTkFrame(details_frame, fg_color="transparent")
        contact_row.pack(pady=1, anchor="w")
        contact_label = ctk.CTkLabel(contact_row, text="Contact: ")
        contact_label.pack(side="left")
        email_label = ctk.CTkLabel(contact_row, text="ad277@uni-heidelberg.de", text_color="#1f538d", cursor="hand2")
        email_label.pack(side="left")
        email_label.bind("<Enter>", lambda e: email_label.configure(text_color="#14375e"))
        email_label.bind("<Leave>", lambda e: email_label.configure(text_color="#1f538d"))
        email_label.bind("<Button-1>", lambda e: self.open_link("mailto:ad277@uni-heidelberg.de"))
        info_row = ctk.CTkFrame(details_frame, fg_color="transparent")
        info_row.pack(pady=1, anchor="w")
        info_label = ctk.CTkLabel(info_row, text="Further information: ")
        info_label.pack(side="left")
        github_label = ctk.CTkLabel(
            info_row,
            text="https://github.com/hwbuehler/hgsfp-survey-tool/tree/main#",
            text_color="#1f538d",
            cursor="hand2",
        )
        github_label.pack(side="left")
        github_label.bind("<Enter>", lambda e: github_label.configure(text_color="#14375e"))
        github_label.bind("<Leave>", lambda e: github_label.configure(text_color="#1f538d"))
        github_label.bind("<Button-1>", lambda e: self.open_link("https://github.com/hwbuehler/hgsfp-survey-tool/tree/main#"))

        close_button = ctk.CTkButton(about_win, text="Close", command=about_win.destroy)
        close_button.pack(padx=10, pady=6)

        about_win.update_idletasks()
        about_win.minsize(about_win.winfo_reqwidth(), about_win.winfo_reqheight())

    def open_link(self, url):
        webbrowser.open_new_tab(url)

    def OpenFile(self, choice=None) -> None:
        name_in_list = self.dropdown.get()
        if not self.filepaths or name_in_list not in self.filepaths:
            CTkMessagebox(
                title='Selection Warning',
                message='No file selected or analysis not yet run.',
                icon='warning',
            )
            return
        filename = self.filepaths[name_in_list]
        full_path = os.path.join(self.output_path.get(), filename)
        if not os.path.exists(full_path):
            CTkMessagebox(
                title='File Not Found',
                message=f'Could not find the file:\n{full_path}',
                icon='warning',
            )
            return
        try:
            os.startfile(full_path)
        except OSError as exc:
            CTkMessagebox(
                title='Open File Error',
                message=f'Failed to open the file:\n{exc}',
                icon='warning',
            )
        #if os.path.exists(full_path):
        #else:
        #    CTkMessagebox(title='Wrong Path Warning',message='Filepath not found !',icon='warning')

    def SetInputPath(self) -> None:
        selected_file = ctk.filedialog.askopenfilename()
        if selected_file:
            self.input_path.set(selected_file)
            self.label_input_path.configure(text=selected_file)

    def SetOutputPath(self) -> None:
        selected_dir = ctk.filedialog.askdirectory()
        if selected_dir:
            self.output_path.set(selected_dir)
            self.label_output_path.configure(text=selected_dir)
    
    def DoAnalysis(self) -> None:
        il_lecture = self.il_input_box.get()
        input_path = self.input_path.get()
        output_path = self.output_path.get()

        if not il_lecture.strip():
            CTkMessagebox(
                title='Industry Lecture Warning',
                message='Please enter an industry lecture title.',
                icon='warning',
            )
            return
        if not os.path.isfile(input_path):
            CTkMessagebox(
                title='Input File Warning',
                message='Please select a valid input JSON file.',
                icon='warning',
            )
            return
        if not os.path.isdir(output_path):
            CTkMessagebox(
                title='Output Path Warning',
                message='Please select a valid output folder.',
                icon='warning',
            )
            return

        try:
            analyzer = SurveyAnalyzer(
                il_title=il_lecture.strip(),
                data_path=input_path,
                output_path=output_path,
                summarize=self.summary.get(),
            )
            titles = list(
                analyzer.ml_titles.union(analyzer.al_titles).union({il_lecture.strip()}).union({'Overall'})
            )
            titles.sort()
            self.filepaths = {}
            self.dropdown.configure(values=titles)
            for elem in titles:
                safe_name = elem.lower().replace(' ', '_')
                self.filepaths[elem] = f'results_{safe_name}.pdf'
            analyzer.PerformAutomatedAnalysis()
        except Exception as exc:
            CTkMessagebox(
                title='Analysis Error',
                message=f'Analysis failed:\n{exc}',
                icon='warning',
            )
            return

        CTkMessagebox(
            title='Analysis Info',
            message='Analysis finished successfully!',
            icon='check',
        )

if __name__=='__main__':
    app = MainWindow()
    app.mainloop()
