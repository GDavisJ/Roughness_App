"""
Module Name: PRF_GUI
Project: Data-to-Vision
Owner: Gary Davis
Class Description: This class is used to create the application GUI.
"""

import sys, os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib
import sys
from matplotlib.backends.backend_gtk3 import (
    NavigationToolbar2GTK3 as NavigationToolbar)
from matplotlib.backends.backend_gtk3agg import (
    FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.figure import Figure
import numpy as np
from PRF_Controller import PRF_Controller
sysArg = sys.argv


class NavigationToolbar(NavigationToolbar):
    # only display the buttons we need
    toolitems = [t for t in NavigationToolbar.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom', 'Save')]

#This class is used to change the vert and horiz lines on the contour plot and change the x/y profile plots.
class Cursor(object):
    def __init__(self):
        self.ax = ''
        self.lx = ''
        self.ly = ''
        self.tstObj = None
        self.coodsList = None

    def set_ax(self, ax, tstObj, ctrlObj):
        self.ax = ax
        self.lx = ax.axhline(color='b')  # the horiz line
        self.ly = ax.axvline(color='r')  # the vert line
        self.tstObj = tstObj
        self.coodsList = ctrlObj
        self.pltX=1
        self.pltY=2
        if len(self.tstObj) ==5:
            self.pltX=2
            self.pltY=3


    #Mouse event data is used to get the plot x/y location.
    def mouse_Click(self, event):
        if not event.inaxes and not event.dblclick:
            return

        x, y = event.xdata, event.ydata
        # update the line positions
        self.lx.set_ydata(y)
        self.ly.set_xdata(x)
        self.tstObj[self.pltX].clear()
        self.tstObj[self.pltY].clear()
        profileList = self.coodsList.getProfiles(y, x)
        self.tstObj[self.pltX].plot(profileList[0],profileList[1],color='b')
        self.tstObj[self.pltX].set_title("X Profile", fontsize=12)
        self.tstObj[self.pltX].set_xlabel("X", fontsize=12)
        self.tstObj[self.pltX].set_ylabel("Z", fontsize=12)
                
        self.tstObj[self.pltY].plot(profileList[2],profileList[3],color='r')
        self.tstObj[self.pltY].set_title("Y Profile", fontsize=12)
        self.tstObj[self.pltY].set_xlabel("Y", fontsize=12)
        self.tstObj[self.pltY].set_ylabel("Z", fontsize=12)

        
        self.ax.figure.canvas.draw()
        self.tstObj[self.pltX].figure.canvas.draw()
        self.tstObj[self.pltY].figure.canvas.draw()
        
        

    

class PRF_GUI(Gtk.Window):
    def __init__(self):
        self.FPath = ''
        self.FName = ''
        self.selectedAnalysis = ''
        self.selectedFilt = ''
        self.analysisList = ['Plot Only','Pad','Roughness','Via']
        self.analysis_store = Gtk.ListStore(str)
        self.filtList = ['None','Gaussian Low Pass', 'Gaussian High Pass']
        self.filt_store = Gtk.ListStore(str)
        self.ctrlObj = None
        self.bgColor = '#FFFFFF'
        self.readIniFile()
        self.ascii_ini = []

        #Set the main window properties
        Gtk.Window.__init__(self, title="PRF ASCII Analysis")
        mainHeader = Gtk.HeaderBar()
        mainHeader.set_show_close_button(True)
        self.set_titlebar(mainHeader)
        self.set_resizable(False)
        self.set_border_width(10)
        self.settings = Gtk.Settings.get_default()
        #self.settings.set_property("gtk-theme-name", "Nocturnal-Blue")
        #self.settings.set_property("gtk-theme-name", "Juno-palenight")

        #Create a grid to store all the objects
        self.grid = Gtk.Grid(column_homogeneous=False, column_spacing=10, row_spacing=10)
        self.add(self.grid)
        

        #Create the browse button and set properties
        self.openAsciiLabel = Gtk.Label(label="Open ASCII: ")
        self.grid.attach(self.openAsciiLabel, 0, 0, 1, 1)
        self.openEntry = Gtk.Entry()
        self.openEntry.set_editable(False)
        self.grid.attach(self.openEntry, 1, 0, 80, 1)
        self.browseBtn = Gtk.Button(label="Browse")
        self.browseBtn.set_size_request(50, 20)
        self.browseBtn.connect("clicked", self.on_browse_button_clicked)
        self.grid.attach(self.browseBtn, 81, 0, 1, 1)


        #Create Tip/Tilt Removal toggle button
        self.tipTiltBtn = Gtk.CheckButton(label="Remove Tilt")
        self.tipTiltBtn.connect("toggled", self.on_tiptilt_button_clicked)
        self.grid.attach(self.tipTiltBtn, 31, 1, 1, 1)


        #Create Theme toggle button
        self.themeBtn = Gtk.CheckButton(label="Dark-Theme")
        self.themeBtn.connect("toggled", self.on_themeBtn_button_clicked)
        self.grid.attach(self.themeBtn, 82, 0, 1, 1)
        self.fig = Figure(figsize=(5, 4), dpi=100)
        
        if self.bgColor == '#292929':
            self.bgColor = '#292929' #Needed just in case someone messes with the config file
            self.themeBtn.set_active(True)
        else:
            self.bgColor = '#FFFFFF'
            self.themeBtn.set_active(False)
        self.fig.set_facecolor(self.bgColor)


        #Create the analysis options and set properties
        self.analysisLabel = Gtk.Label(label="Analysis: ")
        self.grid.attach(self.analysisLabel, 0, 1, 1, 1)
        self.analysisCombobox = Gtk.ComboBox.new_with_model(self.analysis_store)
        self.analysisCombobox.connect("changed", self.on_analysisCombobox_changed)
        #self.filterCombobox.set_sensitive(False)
        renderer_text = Gtk.CellRendererText()
        self.analysisCombobox.pack_start(renderer_text, True)
        self.analysisCombobox.add_attribute(renderer_text, "text", 0)
        self.grid.attach(self.analysisCombobox, 1, 1, 30, 1)
        for item in self.analysisList: self.analysis_store.append([item])
        self.analysisCombobox.set_active(0)


        #Create the filter options and set properties
        self.filterLabel = Gtk.Label(label="Filter: ")
        self.grid.attach(self.filterLabel, 0, 2, 1, 1)
        self.filterCombobox = Gtk.ComboBox.new_with_model(self.filt_store)
        self.filterCombobox.connect("changed", self.on_filtCombobox_changed)
        #self.filterCombobox.set_sensitive(False)
        renderer_text = Gtk.CellRendererText()
        self.filterCombobox.pack_start(renderer_text, True)
        self.filterCombobox.add_attribute(renderer_text, "text", 0)
        self.grid.attach(self.filterCombobox, 1, 2, 30, 1)
        for item in self.filtList: self.filt_store.append([item])
        self.filterCombobox.set_active(0)
        

        #Create the close button and set properties
        self.closeBtn = Gtk.Button(label="Close")        
        self.closeBtn.set_size_request(50, 20)
        self.closeBtn.connect("clicked", self.on_close_button_clicked)
        self.grid.attach(self.closeBtn, 99, 80, 1, 1)


        #Create the clear button and set properties
        self.clearBtn = Gtk.Button(label="Clear")        
        self.clearBtn.set_size_request(50, 20)
        self.clearBtn.connect("clicked", self.on_clear_button_clicked)
        self.grid.attach(self.clearBtn, 98, 80, 1, 1)


        #Create the save all button and set properties
        self.saveBtn = Gtk.Button(label="Save All")        
        self.saveBtn.set_size_request(50, 20)
        self.saveBtn.connect("clicked", self.on_save_button_clicked)
        self.grid.attach(self.saveBtn, 97, 80, 1, 1)



        #Create an empty matplotlib figure
        self.vbox = Gtk.VBox()
        self.canvas = FigureCanvas(self.fig)
        self.vbox.pack_start(self.canvas, True, True, 0)
        self.grid.attach(self.vbox, 0, 3, 100, 70) #(Obj, col, row, len, width)
        # Create toolbar
        toolbar = NavigationToolbar(self.canvas, self)
        self.vbox.pack_start(toolbar, False, False, 10)
        self.cursor = Cursor()


        #Gets system args passed to .exe (for example: someone changes the .asc to open with this script, it will use the arg to open the .asc file).
        #If .asc file gets double clicked, the file will automatically get loaded and plots created.
        if len(sysArg) >= 2:
            self.sysArgOpen()

    #Browse button used to open file chooser dialog and filter files so only .asc files are displayed. 
    def on_browse_button_clicked(self, widget):
        parent = self.get_toplevel()
        FCHeader = Gtk.HeaderBar()
        FCHeader.set_show_close_button(True)
        
        dialog = Gtk.FileChooserDialog(title="Open..",
                                       parent=parent,
                                       action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        dialog.set_titlebar(FCHeader)
        FCHeader.show()

        #Add a filter to only find ASCII files
        filter = Gtk.FileFilter()
        filter.set_name('.asc')
        filter.add_pattern('*.asc')
        dialog.add_filter(filter)
        response = dialog.run()

        
        if response == Gtk.ResponseType.OK:
            if len(dialog.get_filename().split('.asc')) == 2:
                try:
                    self.FPath = '\\'.join(dialog.get_filename().split('\\')[:-1])+'\\'
                    self.FName = dialog.get_filename().split('\\')[-1]
                    self.openEntry.set_text(self.FName)

                    #Open the file and create a new figure
                    self.ctrlObj = PRF_Controller(self.FName, self.FPath, self.selectedAnalysis, self.tipTiltBtn.get_active(), self.selectedFilt)
                    self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                    self.ReplaceFigure(self.fig)
                except:
                    message  = self.userMessageDialog('File Error', 'The file selected uses the wrong naming convention.', Gtk.MessageType.ERROR)
                    message.run()
                    message.destroy()
                    self.openEntry.set_text("")
        dialog.destroy()
            
                
        
    #Tilt button event for data tilt removal (LMS plane fit and normalization).
    def on_tiptilt_button_clicked(self, widget):
        if self.openEntry.get_text() != '':
                self.ctrlObj.updateProperties(self.tipTiltBtn.get_active(), self.selectedFilt)
                self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                self.ReplaceFigure(self.fig)

    #Theme button event to change application theme and save the results to a config file.
    def on_themeBtn_button_clicked(self, widget):
        self.settings.set_property("gtk-application-prefer-dark-theme", self.themeBtn.get_active())
        if self.themeBtn.get_active():
            self.fig.set_facecolor('#292929')
            self.bgColor = '#292929'
            self.saveIniFile()
            if self.openEntry.get_text() != '':
                self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                self.ReplaceFigure(self.fig)
            
        else:
            self.fig.set_facecolor('#FFFFFF')
            self.bgColor = '#FFFFFF'
            self.saveIniFile()
            if self.openEntry.get_text() != '':
                self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                self.ReplaceFigure(self.fig)
        self.fig.canvas.draw()
        
        

    #Close button event to close/ destroy the application.
    def on_close_button_clicked(self, widget):
        Gtk.Window.destroy(self)
        Gtk.main_quit()

    #Clear button event used to set the GUI back to default conditions.
    def on_clear_button_clicked(self, widget):
        self.openEntry.set_text("")
        self.analysisCombobox.set_active(0)
        self.filterCombobox.set_active(0)
        self.tipTiltBtn.set_active(False)
        for element in self.vbox.get_children():
            self.vbox.remove(element)
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)  # a Gtk.DrawingArea        
        self.vbox.pack_start(self.canvas, True, True, 0)
        toolbar = NavigationToolbar(self.canvas, self)
        self.vbox.pack_start(toolbar, False, False, 10)
        self.show_all()
      

    #Save button event used to save plots and data.
    def on_save_button_clicked(self, widget):
        self.ctrlObj.getFigObj(bgColor=self.bgColor, saveFig=True)
        message  = self.userMessageDialog('Save Files', 'Files Successfully Saved!!!',
                                          Gtk.MessageType.INFO)
        message.run()
        message.destroy()


    #Combobox event to change the analysis type (Example: Change PlotOnly to Roughness)
    def on_analysisCombobox_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            self.selectedAnalysis = model[tree_iter][0]
            if self.openEntry.get_text() != '':
                self.ctrlObj = PRF_Controller(self.FName, self.FPath, self.selectedAnalysis, self.tipTiltBtn.get_active(), self.selectedFilt)
                self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                self.ReplaceFigure(self.fig)
                
    #Filter combobox event used to add a filter to the data. The information gets passed to the analysis object to get updated.
    def on_filtCombobox_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            self.selectedFilt = model[tree_iter][0]
            if self.openEntry.get_text() != '':
                self.ctrlObj.updateProperties(self.tipTiltBtn.get_active(), self.selectedFilt)
                self.fig = self.ctrlObj.getFigObj(bgColor=self.bgColor)
                self.ReplaceFigure(self.fig)
            
    #Method used to remove all the children from the vbox so we can fill it with new objects
    def ReplaceFigure(self, fig):
        for element in self.vbox.get_children():
            self.vbox.remove(element)
        self.canvas = FigureCanvas(self.fig)  # a Gtk.DrawingArea        
        self.vbox.pack_start(self.canvas, True, True, 0)
        toolbar = NavigationToolbar(self.canvas, self)
        self.vbox.pack_start(toolbar, False, False, 10)
        self.cursor.set_ax(self.fig.get_axes()[0], self.fig.get_axes(), self.ctrlObj)
        self.fig.canvas.mpl_connect('button_press_event', self.cursor.mouse_Click)
        self.show_all()


                
    #Method used to open a file if an argument is passed to the .exe
    def sysArgOpen(self):
        if len(sysArg[1].split('.asc')) == 2:
                self.FPath = '\\'.join(sysArg[1].split('\\')[:-1])+'\\'
                self.FName = sysArg[1].split('\\')[-1]
                self.openEntry.set_text(self.FName)
                #Open the file and create a new figure
                self.ctrlObj = PRF_Controller(self.FName, self.FPath, self.selectedAnalysis, self.tipTiltBtn.get_active(), self.selectedFilt)
                self.fig = self.ctrlObj.getFigObj()
                self.ReplaceFigure(self.fig)

    #Method used to display a message to the user.
    def userMessageDialog(self, messageTitle='', messageText='', messageType=Gtk.MessageType.INFO):
        parent = self.get_toplevel()
        MessHeader = Gtk.HeaderBar()
        MessHeader.set_show_close_button(True)
        message = Gtk.MessageDialog(parent=parent, title=messageTitle,
                                    modal=Gtk.DialogFlags.MODAL,
                                    message_type=messageType,
                                    buttons=Gtk.ButtonsType.CLOSE,
                                    text=messageText)
        message.set_titlebar(MessHeader)
        message.show_all()
        return message

    #Method used to read the config file contents
    def readIniFile(self):
        openIni = os.path.join(os.path.dirname(__file__), 'ASCII.ini')
        file = open(openIni, "r")
        self.ascii_ini = file.readlines()
        file.close()
        self.bgColor = str(self.ascii_ini[0].split('=')[1]).strip()

    #Method used to save config file
    def saveIniFile(self):
        saveIni = os.path.join(os.path.dirname(__file__), 'ASCII.ini')
        file = open(saveIni, "w")
        file.write('bgColor='+self.bgColor)
        file.close()


win = PRF_GUI()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
