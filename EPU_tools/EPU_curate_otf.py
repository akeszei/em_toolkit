## Written by: Alexander Keszei ver.1 2024-10-01

"""
    Interactive matplotlib gui to read data from a logfile and adjust thresholds for two key parameters. 

    The GUI is built in __main__ and the key objects & data are stored int the Parameters object for a single authoritative location for those objects & variables 
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button


####################################
#region :: Class :: Parameters
####################################
class Parameters:
    """
        Store all parametes and objects needed in a single container object that we can easily reference once 
    """
    def __init__(self, logfile):

        self.blue = 'tab:blue'
        self.red = 'tab:red'
        self.marker_size = 5
        self.ctf_fit_value = 9
        self.dZ_min = 1.25
        self.dZ_max = 3
        self.logfile = logfile
        self.out_fname = "rejected_mics.txt"

        ## graph elements :: hlines
        self.ctf_line = None
        self.ctf_line_text = None
        self.dZ_max_line = None
        self.dZ_max_line_text = None
        self.dZ_min_line = None 
        self.dZ_min_line_text = None
        
        ## graph elements :: DataFrame
        self.csv_data = None  
        return 
    
    def set_csv_data(self, csv_data):
        self.csv_data = csv_data
        return 

    def add_hlines(self, ctf_line, ctf_line_text, dZ_min_line, dZ_min_line_text, dZ_max_line, dZ_max_line_text):
        self.ctf_line = ctf_line 
        self.ctf_line_text = ctf_line_text
        self.dZ_min_line = dZ_min_line
        self.dZ_min_line_text = dZ_min_line_text
        self.dZ_max_line = dZ_max_line 
        self.dZ_max_line_text = dZ_max_line_text
        return 
    
    def set_ctf_fit(self, expression):
        try:
            new_ctf_fit = float(expression)
            self.ctf_fit_value = new_ctf_fit
            print(" New CTF FIT max given: %s" % self.ctf_fit_value)

        except:
            print(" !! ERROR !! Could not parse input expression as CTF fit (%s), will not update" % expression)

        return 

    def set_dZ_range(self, expression):
        ## parse the expression into its min and max values 
        dZ_values = str(expression).split(',')
        if len(dZ_values) != 2:
            print(" ERROR :: Could not parse entry widget for dZ values, try a range in the form: x,y")
            return 
        try:
            dZ_min = float(dZ_values[0])
            dZ_max = float(dZ_values[1])

            if dZ_min > dZ_max:
                print(" ERROR :: The lower dZ values given is larger than the larger dZ values (i.e. x > y for the given entry x,y)")
                return 
            else:
                ## set the values 
                self.dZ_min = dZ_min 
                self.dZ_max = dZ_max
                print(" New dZ range given: (%s, %s)" % (dZ_min, dZ_max) )

        except:
            print(" ERROR :: Could not parse entry for dZ value as floats, check input values and ensure they are of the form: x,y")
        return 
#endregion 
####################################

####################################
#region :: Global functions
####################################
def submit(expression, PARAMETERS, WIDGET = None):
    """ WIP need to have the function run over all attributes (DZ and CTF fit) every time, hence the previous values need to be saved in buffer! Updating any one widget will always trigger both scans 
    """
    ## take in the new values from the widget, adjusting behavior as necessary 
    if WIDGET == 'ctf_fit':
        PARAMETERS.set_ctf_fit(expression)

        ## update line and text objects on graph 
        PARAMETERS.ctf_line.remove()
        PARAMETERS.ctf_line = ax[1].axhline(y=PARAMETERS.ctf_fit_value, c = PARAMETERS.red, linewidth=1, zorder=0)
        PARAMETERS.ctf_line_text.set_text(str(PARAMETERS.ctf_fit_value))
        PARAMETERS.ctf_line_text.set_position((1.01,PARAMETERS.ctf_fit_value))

    elif WIDGET == 'dZ':
        PARAMETERS.set_dZ_range(expression)

        ## update line and text objects on graph 
        PARAMETERS.dZ_min_line.remove()
        PARAMETERS.dZ_max_line.remove()
        PARAMETERS.dZ_min_line = ax[0].axhline(y=PARAMETERS.dZ_min, c = PARAMETERS.red, linewidth=1, zorder=0)
        PARAMETERS.dZ_max_line = ax[0].axhline(y=PARAMETERS.dZ_max, c = PARAMETERS.red, linewidth=1, zorder=0)
        PARAMETERS.dZ_min_line_text.set_text(str(PARAMETERS.dZ_min))
        PARAMETERS.dZ_min_line_text.set_position((1.01,PARAMETERS.dZ_min))
        PARAMETERS.dZ_max_line_text.set_text(str(PARAMETERS.dZ_max))
        PARAMETERS.dZ_max_line_text.set_position((1.01,PARAMETERS.dZ_max))
    elif WIDGET == 'Refresh':
        print(" Reload data from logfile (%s)" % PARAMETERS.logfile)
    else:
        print(" ERROR :: Unknown WIDGET flag called")

    ## update each point based on the new cutoffs 
    PARAMETERS.csv_data['color'] = PARAMETERS.blue ## reset color data
    for row in PARAMETERS.csv_data.iterrows():
        index, row_obj = row

        ## step 1 :: check if the point fails due to CTF cutoff 
        CTF_FIT = row_obj['ctf_fit']
        if CTF_FIT > PARAMETERS.ctf_fit_value:
            PARAMETERS.csv_data.at[index, 'color'] = PARAMETERS.red
            continue 
        else:
            ## step 2 :: check if otherwise the point fails due to dZ out-of-range 
            dZ_FIT = row_obj['dZ']
            if dZ_FIT > PARAMETERS.dZ_max or dZ_FIT < PARAMETERS.dZ_min :
                PARAMETERS.csv_data.at[index, 'color'] = PARAMETERS.red
                
    ## plot the points 
    PARAMETERS.csv_data.plot(x='index', y='dZ', s = PARAMETERS.marker_size, kind='scatter', ax=ax[0], c = PARAMETERS.csv_data['color']) 
    PARAMETERS.csv_data.plot(x='index', y='ctf_fit', s = PARAMETERS.marker_size, kind='scatter', ax=ax[1], c = PARAMETERS.csv_data['color'])  

    plt.draw()
    return 

def refresh(PARAMETERS):
    csv_data = pd.read_csv(PARAMETERS.logfile, delimiter=r"\s+")
    csv_data['color'] = PARAMETERS.blue
    PARAMETERS.set_csv_data(csv_data)
    ## use the submit function to call the redraw
    submit('', PARAMETERS, WIDGET = 'Refresh')
    return 

def write_file(PARAMETERS):
    ## prepare the file to save in
    with open(PARAMETERS.out_fname, 'w') as f:

        ## iterate over all data points and use the color as a signifier if it shuld be kept or removed 
        rejected = 0
        for row in PARAMETERS.csv_data.iterrows():
            index, row_obj = row
            color = row_obj['color'] #tab:red == rejected, tab:blue == kept
            if 'red' in color:
                rejected += 1
                mic_index = row_obj['index'] 
                mic_name = row_obj['mic_name']
                # print(" rejected micrograph :: %s %s" % (mic_index, mic_name))
                f.write("%s \n" % mic_name)
    print(" %s micrographs were rejected (written to file: %s)" % (rejected, PARAMETERS.out_fname))
    return
#endregion 
####################################


####################################
#region :: Run block
####################################
if __name__ == "__main__":

    ## setup defaults 
    logfile = "otf.log"
    PARAMETERS = Parameters(logfile)

    ## import the logfile as a Pandas DataFrame 
    csv_data = pd.read_csv(PARAMETERS.logfile, delimiter=r"\s+")
    ## add a new default column for the color mapping on the plotting function 
    csv_data['color'] = PARAMETERS.blue
    PARAMETERS.set_csv_data(csv_data)

    ## setup the parental figure and axes objects 
    fig, ax = plt.subplots(2, 1) #, figsize=(11,7))
    ## make room for the buttons panel below 
    fig.subplots_adjust(bottom=0.3, top=0.97)

    ## setup the axes labels 
    ax[0].set(xlabel="index", ylabel="defocus (microns)") #, title="Avg. dZ")
    ax[1].set(xlabel="index", ylabel="CTF fit (Ang)") #, title="CTF Fit")

    ## intialize horizontal lines indicating the cutoff point for each graph  
    ctf_line = ax[1].axhline(y=0, c="red",linewidth=0,zorder=0)
    dZ_max_line = ax[0].axhline(y=0, c="red",linewidth=0,zorder=0)
    dZ_min_line = ax[0].axhline(y=0, c="red",linewidth=0,zorder=0)

    ## initialize text beside each line 
    ctf_text = ax[1].text(1.01, 0, "", verticalalignment='center', horizontalalignment='left', transform=ax[1].get_yaxis_transform(), color='red', fontsize=10)
    dZ_max_text = ax[0].text(1.01, 0, "", verticalalignment='center', horizontalalignment='left', transform=ax[0].get_yaxis_transform(), color='red', fontsize=10)
    dZ_min_text = ax[0].text(1.01, 0, "", verticalalignment='center', horizontalalignment='left', transform=ax[0].get_yaxis_transform(), color='red', fontsize=10)

    ## load the hline objects into the Parameters object for ease-of-use 
    PARAMETERS.add_hlines(ctf_line, ctf_text, dZ_min_line, dZ_min_text, dZ_max_line, dZ_max_text)
    
    ## set up refresh button and behavior 
    ax_refresh = fig.add_axes([0.81, 0.05, 0.1, 0.075])
    button_refresh = Button(ax_refresh, 'Refresh')
    button_refresh.on_clicked(lambda event: refresh(PARAMETERS))

    ## set up write button and behavior 
    ax_button_write = fig.add_axes([0.41, 0.05, 0.1, 0.075])
    button_write = Button(ax_button_write, 'Print')
    button_write.on_clicked(lambda event: write_file(PARAMETERS))

    ## set up text input widgets 
    axbox = fig.add_axes([0.2, 0.05, 0.15, 0.05])
    text_box = TextBox(axbox, "CTF fit max: ", textalignment="right")
    text_box.on_submit(lambda expression: submit(expression, PARAMETERS, WIDGET = 'ctf_fit'))

    axbox2 = fig.add_axes([0.2, 0.15, 0.15, 0.05])
    text_box2 = TextBox(axbox2, "Defocus range: ", textalignment="right")
    text_box2.on_submit(lambda expression: submit(expression, PARAMETERS, WIDGET = 'dZ'))

    text_box.set_val(str(PARAMETERS.ctf_fit_value))  # Trigger `submit` with the initial string.
    text_box2.set_val("%s,%s" % (PARAMETERS.dZ_min, PARAMETERS.dZ_max))  # Trigger `submit` with the initial string.


    plt.show()

#endregion 
####################################