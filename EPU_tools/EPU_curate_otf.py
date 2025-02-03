#!/usr/bin/env python3

## Author : A. Keszei 

## 2025-02-03: version 1 finished

def usage():
    print(
"""
    ## Dependencies: 
        $ pip install panel hvplot starfile
    ## Run this script from the output directory of EPU_on-the-fly.py (containing ctf.star file) using panel:
        $ panel serve /programs/akeszei/bin/EPU_curate_otf.py 
    ## The webapp can be found at the address written in the terminal, typically at: host:5006/EPU_curate_otf
"""
    )
    exit()

if __name__ == "__main__":
    usage()

######################################
#region GLOBALS 
######################################
PRIMARY_COLOR = "#0072B5"
SECONDARY_COLOR = "#B54300"
BLUE = "#1984c5"
RED = "#EE4B2B"
STAR_FILE = "ctf.star"
dZ_MAX = None
dZ_MIN = None
CTFFIT_MAX = None
CTFFIT_MIN = None
ACCEPTED = []
REJECTED = []
SIDEBAR_WIDTH = 250
RAW_CSS="""
.sidenav#sidebar {
    background-color: grey;
}
"""
#endregion 
######################################

import os 
import hvplot.pandas
import holoviews as hv
import numpy as np
import pandas as pd
import starfile as sf 
from functools import partial # REF: https://docs.python.org/3/library/functools.html
import panel as pn
from PIL import Image as PIL_Image 

@pn.cache
def get_data(star_file, VERBOSE = True):
    """ Unpact the .STAR file into an easily manipulated data frame object
    """
    df = sf.read(star_file)
    df, reject_list, approve_list = assign_point_colors(df)

    if VERBOSE: 
        print(df)

    return df 

def assign_point_colors(df):
    """ Run through the DataFrame object and add/update the assigned color value for each point 
    """
    global ACCEPTED, REJECTED
    ## add/reset a new column for the color mapping on the plotting function 
    blue = BLUE
    red = RED
    df['color'] = blue

    rejection_list = [] # list of bad micrographs
    approved_list = [] # list of good micrographs
    ## another approach is to look at each file name and then use its unique name to look up its threshold flag in the DataFrame
    for row in df.iterrows():
        index, row_obj = row 
        print(row_obj)

        CTF_FIT = row_obj['CtfFit']
        dZ_FIT = row_obj['dZ']
        mic_name = row_obj["MicrographName"]
        
        ## iterate over all rejection critera one-by-one, skipping rest with `continue` keyword if a failure condition is encountered
        if CTFFIT_MAX != None and CTF_FIT > CTFFIT_MAX:
            df.at[index, 'color'] = red
            rejection_list.append(mic_name)
            continue 

        if CTFFIT_MIN != None and CTF_FIT < CTFFIT_MIN:
            df.at[index, 'color'] = red
            rejection_list.append(mic_name)
            continue 

        if dZ_MAX != None and dZ_FIT > dZ_MAX:
            df.at[index, 'color'] = red
            rejection_list.append(mic_name)
            continue 

        if dZ_MIN != None and dZ_FIT < dZ_MIN:
            df.at[index, 'color'] = red
            rejection_list.append(mic_name)
            continue 
        
        ## if we made it passed all the above checks, then we are looking at a good micrograph
        approved_list.append(mic_name)

    ## write the accepted and rejected lists to the global variable 
    ACCEPTED = approved_list
    REJECTED = rejection_list
    return df, rejection_list, approved_list

def get_plot(df, header, alternate_style = False):
    """Use hvplot to generate an interactive scatter plot
    PARAMETERS 
        df = pandas DataFrame object 
        header = str(), header from DataFrame from which to pull data from
    """
    d = df[header]
    if header == 'dZ':
        y_axis_label = '-μm'
    elif header == 'CtfFit':
        y_axis_label = 'Å'
    if alternate_style:
        # plot = d.hvplot.scatter(height=200, legend=False, color=df['color'], responsive=True, size=40)
        plot = hv.Scatter(d).opts(  tools = ["tap"], 
                                    size = 8, 
                                    height=200, 
                                    responsive=True, ## responsive means it will stretch the axis that is not explicitly defined to fit the UI area 
                                    # nonselection_color='red', 
                                    nonselection_alpha = 0.35, ## range = [0,1] 
                                    ylabel = y_axis_label, 
                                    labelled=['y'], ## labelled =['x', 'y'], informs which axis to actually label 
                                    title = header
                                )  
    else:
        plot = d.hvplot.scatter(height=280, legend=False, color=df['color'], responsive=True, size=40, xlabel = 'index', ylabel = y_axis_label)


    # plot = hv.Scatter(d, linked_axes = False)

    return plot  

def reload_data(event):
    global df, ACCEPTED, REJECTED, template
    print(" REFRESH ")
    pn.state.clear_caches()
    df = get_data(STAR_FILE)

    # ## for testing add an arbitrary point to the dataframe instead of having to open and edit the input file
    # new_row = pd.DataFrame({"MicrographName" : "test_mic", "dZ" : [10], "CtfFit" : [10]})
    # input_dataframe = pd.concat([input_dataframe, new_row], ignore_index = True)
    # print(" Test, ", input_dataframe)

    ## Assign the correct template object for each plot here
    dZ_plot = template.main[0][0][0]
    ctfFit_plot = template.main[0][0][1]
    plots_tab = template.main[0][0]
    analysis_plot = template.main[0][1][0]  

    plots_tab.loading = True
    # dZ_plot.loading = True
    # ctfFit_plot.loading = True
    analysis_plot.loading = True


    dZ_plot.object = get_plot(df, "dZ")
    ctfFit_plot.object = get_plot(df, "CtfFit")
    analysis_plot.object = get_plot(df, "CtfFit", alternate_style = True)

    plots_tab.loading = False
    # dZ_plot.loading = False
    # ctfFit_plot.loading = False
    analysis_plot.loading = False


    ## update the text describing the accpted and rejected values
    # text = "%s/%s micrographs (%s %) are marked as out of range based on current thresholds: CTF FIT [%s, %s], dZ RANGE [%s, %s]" % (len(ACCEPTED), len(REJECTED), len(ACCEPTED)/len(REJECTED), CTFFIT_MIN, CTFFIT_MAX, dZ_MIN, dZ_MAX) 
    text = "{}/{} micrographs ({} %) are marked as out of range based on current thresholds: CTF FIT [{}, {}], dZ RANGE [{}, {}]".format(len(REJECTED), len(df.index), 100 * len(REJECTED)/len(df.index), CTFFIT_MIN, CTFFIT_MAX, dZ_MIN, dZ_MAX)
    action_sidebar[1].object = text
    
    return 

def delete_rejected_files(event):
    global REJECTED
    print(" Delete %s images" % len(REJECTED))
    directories = ['movies', 'micrographs']
    for dir in directories:
        ## check the directory exists 
        if os.path.exists(dir):
            ## check the directory for each file in the rejected list 
            for f in REJECTED:
                # f_basename = os.path.splitext(f)[0]
                f_path = os.path.join(dir, f)
                if os.path.exists(f_path):
                    print(" Delete file: %s" % f_path)
                    os.remove(f_path)
                else:
                    print(" File could not be found (perhaps was already deleted) = %s" % f_path)

    return 

def text_updated(widget_event):
    global dZ_MAX, dZ_MIN, CTFFIT_MAX, CTFFIT_MIN
    print(" text boxes updated")
    print(" enter pressed? ", widget_event.obj.enter_pressed)
    # print(widget_event, type(widget_event))

    # widget_name = widget_event.obj.name.lower()
    # widget_value = widget_event.obj.value
    # if 'dz' in widget_name:
    #     if 'max' in widget_name: dZ_MAX = set_threshold(widget_value)
    #     if 'min' in widget_name: dZ_MIN = set_threshold(widget_value)
    # elif 'ctf' in widget_name:
    #     if 'max' in widget_name: CTFFIT_MAX = set_threshold(widget_value)
    #     if 'min' in widget_name: CTFFIT_MIN = set_threshold(widget_value)

    ## read all widgets and try to assign their values 
    dZ_MAX = set_threshold(dZ_max_input.value)
    dZ_MIN = set_threshold(dZ_min_input.value)
    CTFFIT_MAX = set_threshold(ctfFit_max_input.value)
    CTFFIT_MIN = set_threshold(ctfFit_min_input.value)

    print(" Set thresholds: ")
    print("     dZ_MAX = ", dZ_MAX)
    print("     dZ_MIN = ", dZ_MIN)
    print("     CTFFIT_MAX = ", CTFFIT_MAX)
    print("     CTFFIT_MIN = ", CTFFIT_MIN)

    reload_data("empty_event")
    return 

def set_threshold(value):
    try: 
        value = float(value)
    except:
        value = None
    return value 

def update():
    global df
    """ Compare the loaded data to the potential updated data, if different then run the update otherwise do nothing """
    ## check if the toggle for continuous update is on before proceeding 
    if not switch_continuous.value:
        return 

    ## read the star file and load it into a fresh DataFrame 
    new_df = sf.read(STAR_FILE)

    ## get the size of the new DataFrame and compare it to the active one in cache  
    if len(new_df.index) != len(df.index):
        ## there is a difference in size, so we should run a refresh  
        empty_event = ""
        reload_data(empty_event)        

def get_img(im_path, title, width):
    ## Zoomable image, ref: https://discourse.holoviz.org/t/how-to-enable-a-zoom-tool-on-a-panel-image/7524/4

    if not os.path.exists(im_path):
        print(" file NOT found!! %s" % im_path)
        blank_image = np.zeros((width, width, 4), np.uint8)

        blank_image[:] = 50

        display_img = hv.RGB(blank_image).opts(aspect = 'square', width = width, xaxis = None, yaxis = None, title = title, toolbar = None) 
        return display_img
        
    else:
        print(" file found: %s" % im_path)
        ## load image into array using PIL & NumPY
        # im_obj = PIL_Image.open(tempfile)
        # im_obj.point(lambda p: p*0.0039063096, mode='RGB')
        # im_obj = im_obj.convert('RGB')
        # im_array = np.array(im_obj)

        im_obj_bw = PIL_Image.open(im_path)
        im_obj_rgb = PIL_Image.new("RGB", im_obj_bw.size)
        im_obj_rgb.paste(im_obj_bw)
        im_array = np.array(im_obj_rgb)
        print(" im loaded: ", im_array.shape)
    # im = hv.RGB.load_image(tempfile, height = 250, width = 250)
        display_img = hv.RGB(im_array).opts(aspect = 'square', width = width, xaxis = None, yaxis = None, title = title, toolbar = None)#, width = 500),#.servable()
        return display_img

def on_scatterplot_click(index):
    if len(index) > 0:
        i = index[0]
        update_imgs(i)
    else:
        update_imgs(-1)
    return 

def update_imgs(i):
    global df, template

    jpg_dir = 'jpg/'
    ## use the index to find the name of the micrograph and its corresponding grid square & atlas images 
    num_plotted_points = len(df.index)
    print(" update imgs, i = %s, num_plotted_points = %s" % (i, num_plotted_points))
    if i <= num_plotted_points - 1 and i > -1:
        mic_fname = df['MicrographName'][i]
        mic_path = os.path.join(jpg_dir, os.path.splitext(mic_fname)[0] + ".jpg")
        grid_square_id = "_".join(mic_fname.split('_')[:2])
        matched_grid_square_jpg_path = os.path.join(jpg_dir, grid_square_id + ".jpg") 
        matched_grid_atlas_jpg_path = os.path.join(jpg_dir, grid_square_id + "_Atlas.jpg")

        ## get the template objects for the images 
        atlas_obj = template.main[0][1][1][0][0]
        square_obj = template.main[0][1][1][1][0]
        mic_obj = template.main[0][1][1][2][0]

        atlas_obj.loading = True
        square_obj.loading = True
        mic_obj.loading = True

        atlas_obj.object = get_img(matched_grid_atlas_jpg_path, 'Atlas', 350)
        square_obj.object = get_img(matched_grid_square_jpg_path, 'Square', 350)
        mic_obj.object = get_img(mic_path, 'Micrograph', 350)

        atlas_obj.loading = False
        square_obj.loading = False
        mic_obj.loading = False

    return
 

pn.extension(design="material", sizing_mode="stretch_width")

text = """
## On-the-fly data curation

Follow data quality live and set thresholds at the end of the session to remove bad micrographs from the set prior to starting processing.
"""
button_refresh = pn.widgets.Button(name="Refresh", button_type="primary", max_width=100,)
switch_continuous = pn.widgets.Switch(name='Switch', value = False, max_width = 20, align = 'center')

dZ_max_input = pn.widgets.TextInput(name='dZ max (-μm)', placeholder='')
dZ_min_input = pn.widgets.TextInput(name='dZ min (-μm)', placeholder='')
ctfFit_max_input = pn.widgets.TextInput(name='CTF fit max (Å)', placeholder='')
ctfFit_min_input = pn.widgets.TextInput(name='CTF fit min (Å)', placeholder='')


text_marked = "No micrographs are marked as out of range based on current thresholds: CTF FIT [%s, %s], dZ RANGE [%s, %s]" % (CTFFIT_MIN, CTFFIT_MAX, dZ_MIN, dZ_MAX)
button_delete_marked = pn.widgets.Button(name="Delete marked micrographs & movies", button_type="danger", max_width=200,)
action_sidebar = pn.panel(pn.Column(
    pn.layout.Divider(),
    pn.pane.Markdown(text_marked), 
    button_delete_marked, 
    # max_width = 250, 
    # sizing_mode = 'stretch_width'
))

title_bar = pn.Column(  pn.pane.Markdown(text, margin=(0, 10)),
                        pn.Row(button_refresh, switch_continuous, 'Auto-refresh', max_width = 500),  
                        pn.Spacer(height=5), 
                        pn.Spacer(styles=dict(background='gray'), height=2),
                        # pn.layout.Divider(),
                        pn.Spacer(height=23),
                    )

dZ_sidebar = pn.layout.WidgetBox(
    dZ_max_input, 
    dZ_min_input, 
    max_width=150,
    sizing_mode='stretch_width'
)

ctfFit_sidebar = pn.layout.WidgetBox(
    ctfFit_max_input, 
    ctfFit_min_input,
    max_width=150,
    sizing_mode='stretch_width'
)

df = get_data(STAR_FILE)
dZ_plot = get_plot(df, "dZ")
ctfFit_plot = get_plot(df, "CtfFit")
analysis_plot = get_plot(df, "CtfFit", alternate_style = True)

stream = hv.streams.Selection1D(source=analysis_plot)
stream.add_subscriber(on_scatterplot_click)

## note: HoloViews pane with linked_axes = False ensures that multiple plots on the same serviceable do not respond to the same mouse controls (i.e. ensuring independent zooming and panning), see ref: https://discourse.holoviz.org/t/unlinking-magically-connected-bar-charts/3857/3
dZ_plot = pn.pane.HoloViews(dZ_plot, linked_axes=False)
ctfFit_plot = pn.pane.HoloViews(ctfFit_plot, linked_axes=False)
# analysis_plot = pn.pane.HoloViews(analysis_plot, linked_axes = False)


button_refresh.on_click(reload_data)
# button_refresh.on_click(partial(reload_data, df)) # the functools partial function allows passing callable functions with extra 'coxt' parameters while not needing to supply all parameters (i.e. the event parameter is supplied by the on_click function) 
button_delete_marked.on_click(delete_rejected_files)


## tie the enter pressed event to the execution of the thresholds to avoid constantly calculating point colors 
# dZ_max_input.param.watch(text_updated, 'value')
dZ_max_input.param.watch(text_updated, 'enter_pressed')
dZ_min_input.param.watch(text_updated, 'enter_pressed')
ctfFit_max_input.param.watch(text_updated, 'enter_pressed')
ctfFit_min_input.param.watch(text_updated, 'enter_pressed')

cb = pn.state.add_periodic_callback(update, 2000, timeout=100000)


# jpg_mic_path = 'jpg/GridSquare_7358443_FoilHole_8326055_Data_7370147_0_20250109_002057_Fractions.jpg'
# jpg_square_path = 'jpg/GridSquare_7358443.jpg'
# jpg_atlas_path = 'jpg/GridSquare_7358443_Atlas.jpg'

## load empty images into squares 
atlas_img = get_img('', 'Atlas', 350)
square_img = get_img('', 'Square', 350)
mic_img = get_img('', 'Micrograph', 350)


# Instantiate the template with widgets displayed in the sidebar
template = pn.template.FastListTemplate(
    title='EM on-the-fly dataset analyser',
    sidebar=[title_bar, dZ_sidebar, ctfFit_sidebar],
    main=[],
    # raw_css=[RAW_CSS]
    main_layout = None,
    sidebar_width = SIDEBAR_WIDTH,

)
# Append a layout to the main area, to demonstrate the list-like API
template.main.append(
    pn.Tabs( 
                ('Thresholds', pn.Column(
                                dZ_plot,
                                ctfFit_plot
                            )
                ),
                ('Analysis', pn.Column(
                                analysis_plot,
                                pn.Row(
                                    pn.pane.HoloViews(atlas_img, linked_axes=False),
                                    pn.pane.HoloViews(square_img, linked_axes=False),
                                    pn.pane.HoloViews(mic_img, linked_axes=False)
                                )
                            )
                ),
                ('Options', pn.layout.WidgetBox(action_sidebar)
                )
                    
    )
)
    


template.servable();
