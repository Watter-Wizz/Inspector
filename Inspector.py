"""
# Battery Shutdown Tool 
##### Project:      Siena Battery
##### File:         Inspector.py
##### Author:       Enrique Garcia
##### Description: Tool to set Siena batteries into SHUTDOWN mode for shipment. 
##### (2023-JAN-26) REV3
"""
import time
import pywinusb
import six
import bqcomm
from bqcomm import adapter
import tkinter as ttk
import tkinter.messagebox
from tkinter import *

# Setup constants
BQ40Z50_ADDR = 0x17

# Commands
VOLT_CMD = 0x09
TEMP_CMD = 0x08
CURR_CMD = 0x0A
MAXE_CMD = 0x0C
RSOC_CMD = 0x0D
RCAP_CMD = 0x0F
CCNT_CMD = 0x17
SN_CMD = 0x1C
FCC_CMD = 0x10
SHUTDOWN_CMD = [0x10,0x00]
MFR_BLK_ACC_ADDR = 0x44

# --------------------------------------- MAIN GUI -------------------------------------------

#################   Main GUI ###########################################################################################################
class MainApplication(ttk.Frame):
    
    def CheckAdapter(self):
      if  self.bq_adapter == None:
         #print("Nothing has been connected yet")
         try:
            self.bq_adapter = adapter.Adapter()
            time.sleep(0.1)
            self.bq_adapter.open()
            time.sleep(0.1)
            #fwversion = self.bq_adapter.device.get_version()
            #time.sleep(0.1)
            #adaptername = type(self.bq_adapter.device).__name__
            self.info4.config(text="Connected", bg="green" )
            #self.info6.config(text=str(fwversion), bg="green" )
            #print("Succesfullly Established First Connection with 2400")
         except:
            self.bq_adapter == None
            print(" Could not Establish First Connection")
      else:
         try:
            fwversion = self.bq_adapter.device.get_version()
            #print("Connection still 2400 works")
         except:
            self.bq_adapter = None
            self.info4.config(text="Not Connected", bg="red" )
            #self.info6.config(text="Not Connected", bg="red" )
            #print("Connection was broken")

      self.after(1000, self.CheckAdapter)

    def CheckValues(self):
    
    #Is the Voltage between 8V and 12.3  
      voltage = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, VOLT_CMD)
      time.sleep(0.1)
      self.l2.config(text=str(voltage))
      if 8000 <= voltage <= 12300:
         self.OKlabel1.config(bg="green" , text='Pass')
      else:
         self.OKlabel1.config(bg="red" , text='Fail')

   # Is the current= 0 ?
      current = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, CURR_CMD)
      time.sleep(0.1)
      self.l4.config(text=str(current))
      if current==0:
         self.OKlabel2.config(bg="green" , text='Pass')
      else:
         self.OKlabel2.config(bg="red" , text='Fail')

   # Is the temperature between 10 and 40 degrees ?
      temperature = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, TEMP_CMD)/100
      time.sleep(0.1) 
      self.l6.config(text=str(temperature)) 
      if 10 <= temperature <= 40:
         self.OKlabel3.config(bg="green" , text='Pass')
      else:
         self.OKlabel3.config(bg="red" , text='Fail')

   # Is the max error equal or lower to  2 ?
      maxerror = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, MAXE_CMD)
      time.sleep(0.1)
      self.l8.config(text=str(maxerror)) 
      if 0 <= maxerror <= 2:
         self.OKlabel4.config(bg="green" , text='Pass')
      else:
         self.OKlabel4.config(bg="red" , text='Fail')

   # Is the relative state of charge between 5 and 30% ?
      rsoc = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, RSOC_CMD)
      time.sleep(0.1)
      self.l10.config(text=str(rsoc)) 
      if 5 <= rsoc <= 30:
         self.OKlabel5.config(bg="green" , text='Pass')
      else:
         self.OKlabel5.config(bg="red" , text='Fail')

   # Is the remaining capacity between 500 and 3000 ?
      rcap = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, RCAP_CMD)
      time.sleep(0.1)
      self.l12.config(text=str(rcap))   
      if 500 <= rcap <= 3000:
         self.OKlabel6.config(bg="green" , text='Pass')
      else:
         self.OKlabel6.config(bg="red" , text='Fail')

   # Is the cycle count lower or equal to 5
      cyclecount = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, CCNT_CMD)
      time.sleep(0.1)
      self.l14.config(text=str(cyclecount))    
      if 0 <= cyclecount <= 5:
         self.OKlabel7.config(bg="green" , text='Pass')
      else:
         self.OKlabel7.config(bg="red" , text='Fail')

   # Is the Full Charge Capacity higher than 5820
      fcc = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, FCC_CMD)
      time.sleep(0.1)
      self.l16.config(text=str(fcc))    
      if 5820 < fcc :
         self.OKlabel8.config(bg="green" , text='Pass')
      else:
         self.OKlabel8.config(bg="red" , text='Fail')


   # Is the Serial Number higher than 0004
      serialnumber = self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, SN_CMD)
      time.sleep(0.1)
      self.l18.config(text=str(serialnumber))    
      if 4 <= serialnumber :
         self.OKlabel9.config(bg="green" , text='Pass')
      else:
         self.OKlabel9.config(bg="red" , text='Fail')
      
      time.sleep(0.1)
      self.Shutdown()
         
   
    def CheckConnection(self):
      try:
         # some test
         x= self.bq_adapter.device.smb_read_word(BQ40Z50_ADDR, VOLT_CMD)
         self.info7.config(text="Connected", bg="green")
      except:
         self.info7.config(text="Disconnected", bg="red")
         self.l2.config(text=str(0))
         self.OKlabel1.config(bg="gray" , text="Check")
         self.l4.config(text=str(0))
         self.OKlabel2.config(bg="gray" , text="Check")
         self.l6.config(text=str(0))
         self.OKlabel3.config(bg="gray" , text="Check")      
         self.l8.config(text=str(0))
         self.OKlabel4.config(bg="gray" , text="Check")
         self.l10.config(text=str(0))
         self.OKlabel5.config(bg="gray" , text="Check")
         self.l12.config(text=str(0))
         self.OKlabel6.config(bg="gray" , text="Check")
         self.l14.config(text=str(0))
         self.OKlabel7.config(bg="gray" , text="Check")
         self.l16.config(text=str(0))
         self.OKlabel8.config(bg="gray" , text="Check")
         self.l18.config(text=str(0))
         self.OKlabel9.config(bg="gray" , text="Check")

      # This will run the function in every 1000ms (1 secs).
      self.after(1000, self.CheckConnection)    

    def Shutdown(self):
       self.bq_adapter.device.smb_write_block(BQ40Z50_ADDR, MFR_BLK_ACC_ADDR, SHUTDOWN_CMD)
       time.sleep(0.5)
       self.bq_adapter.device.smb_write_block(BQ40Z50_ADDR, MFR_BLK_ACC_ADDR, SHUTDOWN_CMD)
       #print("Shutdown disabled")

    def __init__(self, master, *args, **kwargs):
        ttk.Frame.__init__(self, master, *args, **kwargs)
        #parent = parent
        #self = ttk.Tk()

        self.bq_adapter = None
        voltage = 0
        current = 0
        temperature = 0
        maxerror = 0
        rsoc = 0
        rcap = 0
        cyclecount = 0
        serialnumber = 0
        fcc = 0

        label = ttk.Label(self, text="Battery Shutdown Tool", fg="white", bg="black", font=("Arial", 26))
        label.grid(row=0,column=2, columnspan=10) 
        
     # The strings from the EV2400 need to come after the communication with the adapter is ready

        info3 = ttk.Label(self, text='Adapter ')
        info3.grid(row=2,column=0) 
        self.info4 = ttk.Label(self, text='Disconnected' )
        self.info4.grid(row=2,column=1) 
        
    # This label info7 Indicates if there is connection with battery  
        self.info7 = ttk.Label(self, text='Disconnected')
        self.info7.grid(row=4,column=1) 

        info8 = ttk.Label(self, text='Battery')
        info8.grid(row=4,column=0)  

        l1 = ttk.Label(self, text='Voltage ' , font=("Arial", 26 ))
        l1.grid(row=5,column=2 , sticky = E ) 
        self.l2 = ttk.Label(self, text=str(voltage) , font=("Arial", 26))
        self.l2.grid(row=5,column=3 , sticky = E) 
        self.OKlabel1 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel1.grid(row=5,column=5) 

        l3 = ttk.Label(self, text='Current', font=("Arial", 26) , anchor='e')
        l3.grid(row=6,column=2 , sticky = E) 
        self.l4 = ttk.Label(self, text=str(current), font=("Arial", 26))
        self.l4.grid(row=6,column=3 , sticky = E)
        self.OKlabel2 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel2.grid(row=6,column=5) 

        l5 = ttk.Label(self, text='Temperature', font=("Arial", 26))
        l5.grid(row=7,column=2 , sticky = E) 
        self.l6 = ttk.Label(self, text=str(temperature), font=("Arial", 26))
        self.l6.grid(row=7,column=3 , sticky = E)
        self.OKlabel3 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel3.grid(row=7,column=5) 

        l7 = ttk.Label(self, text='Max Error', font=("Arial", 26))
        l7.grid(row=8,column=2 , sticky = E) 
        self.l8 = ttk.Label(self, text=str(maxerror), font=("Arial", 26))
        self.l8.grid(row=8,column=3 , sticky = E)
        self.OKlabel4 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel4.grid(row=8,column=5) 

        l9 = ttk.Label(self, text='State of charge', font=("Arial", 26))
        l9.grid(row=9,column=2 , sticky = E) 
        self.l10 = ttk.Label(self, text=str(rsoc), font=("Arial", 26))
        self.l10.grid(row=9,column=3 , sticky = E)
        self.OKlabel5 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel5.grid(row=9,column=5) 

        l11 = ttk.Label(self, text='Remaining Capacity', font=("Arial", 26))
        l11.grid(row=10,column=2 , sticky = E) 
        self.l12 = ttk.Label(self, text=str(rcap), font=("Arial", 26))
        self.l12.grid(row=10,column=3 , sticky = E)
        self.OKlabel6 = ttk.Label(self, text="Check", fg="white", bg="gray", font=("Arial", 26))
        self.OKlabel6.grid(row=10,column=5) 

        l13 = ttk.Label(self, text='Cycle Count', font=("Arial", 26))
        l13.grid(row=11,column=2 , sticky = E) 
        self.l14 = ttk.Label(self, text=str(cyclecount), font=("Arial", 26))
        self.l14.grid(row=11,column=3 , sticky = E)
        self.OKlabel7 = ttk.Label(self, text="Check", fg="white", bg="gray" , font=("Arial", 26))
        self.OKlabel7.grid(row=11,column=5)

        l15 = ttk.Label(self, text='Full Charge Capacity', font=("Arial", 26))
        l15.grid(row=12,column=2 , sticky = E) 
        self.l16 = ttk.Label(self, text=str(fcc), font=("Arial", 26))
        self.l16.grid(row=12,column=3 , sticky = E)
        self.OKlabel8 = ttk.Label(self, text="Check", fg="white", bg="gray" , font=("Arial", 26))
        self.OKlabel8.grid(row=12,column=5)

        l17 = ttk.Label(self, text='Serial Number', font=("Arial", 26))
        l17.grid(row=13,column=2 , sticky = E) 
        self.l18 = ttk.Label(self, text=str(serialnumber), font=("Arial", 26))
        self.l18.grid(row=13,column=3 , sticky = E) 
        self.OKlabel9 = ttk.Label(self, text="Check", fg="white", bg="gray" , font=("Arial", 26))
        self.OKlabel9.grid(row=13,column=5)


        lspace = ttk.Label(self, text="        ")
        lspace.grid(row=5,column=4)
        lspace2 = ttk.Label(self, text="        ")
        lspace2.grid(row=14,column=2)

        B1 = ttk.Button(self, text ="Start", command = self.CheckValues , font=("Calibri", 30))
        B1.grid(row=15,column=2, columnspan=5) 

        self.CheckAdapter()
        self.CheckConnection()
        
  

if __name__ == "__main__":
    root = ttk.Tk()
    root.geometry("750x700") 
    root.title('Battery Shutdown Tool V1.0')
    #root.iconbitmap("Inspector2logo.ico")
    MainApplication(root).pack(side="top", fill="both", expand=True)
    root.mainloop()
    