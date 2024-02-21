"""
# Battery Shutdown Tool 
##### Project:      Siena Battery
##### File:         Inspector-New.py
##### Author:       Enrique Garcia
##### Description: Tool to set Siena batteries into SHUTDOWN mode for shipment. 
##### (2023-JAN-26) REV3
"""
import time
from datetime import date
from dateutil.relativedelta import relativedelta
import pywinusb
import six
import bqcomm
from bqcomm import adapter
import tkinter as ttk
import tkinter.messagebox
from tkinter import *
from constants import commands, device_limits, checks, decode_date

         
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
            self.info1.config(text="Connected", bg="green" )
            self.CheckConnection()
         except:
            self.bq_adapter == None
            print(" Could not Establish First Connection")
      else:
         try:
            fwversion = self.bq_adapter.device.get_version()
            self.info1.config(text="Connected", bg="green" )
            self.CheckConnection()
            # print("Connection still works")
         except:
            self.bq_adapter = None
            self.info1.config(text="Not Connected", bg="red" )
            print("Connection was broken")

      self.after(1000, self.CheckAdapter)

   def CheckConnection(self):
      try:
         # some test
         x = self.bq_adapter.device.smb_read_word(commands["BQ40Z50_ADDR"], commands["VOLT_CMD"])
         self.info2.config(text="Connected", bg="green")

         # Is the Battery Siena or Evoline
         # DeviceName's unit is ASCII
         device_no = self.bq_adapter.device.smb_read_word(commands["BQ40Z50_ADDR"], commands["DEVICE_CMD"])
         time.sleep(0.1)
         if device_no == 958231:
            devicename="Siena"
            self.info3.config(text=str(devicename),bg="green")
            
         elif device_no == 453564918601:
            devicename="EV2400"
            self.info3.config(text=str(devicename),bg="green")
                  
      except:
         self.info2.config(text="Disconnected", bg="red")
         self.info3.config(text="Disconnected", bg="red")
         
         for parameter, info in checks.items():
            info["label"].config(text=str(0))
            info["ok_label"].config(bg="gray", text="Check")

   def CheckValues(self):
      # Define the limits for each device
      status_list=[]
      
      # Read the device name
      device_no = self.bq_adapter.device.smb_read_word(commands["BQ40Z50_ADDR"], commands["DEVICE_CMD"])
      time.sleep(0.1)
      if device_no == 958231:
         devicename="Siena"
         
      elif device_no == 453564918601:
         devicename="EV2400"
   
      # Check if the device name is recognized
      if devicename in device_limits:
        # Perform the checks
         for parameter, info in checks.items():
            value = self.bq_adapter.device.smb_read_word(commands["BQ40Z50_ADDR"], info["cmd"])

            time.sleep(0.1)
            if "scale" and "constant" in info:
               value = value*info["scale"] + info["constant"]
                     
            if "greater_than" in info:
               limit = device_limits[devicename][parameter]
               status = value >= limit
            elif isinstance(device_limits[devicename][parameter], tuple):
               min_limit, max_limit = device_limits[devicename][parameter]
               status = min_limit <= value <= max_limit
            elif "date_check" in info:
               value = decode_date(value)
               presentdate = date.today()
               status = value >= (presentdate - relativedelta(years=device_limits[devicename][parameter])) 
            else:
               status = value == device_limits[devicename][parameter]
            status_list.append(status)

            info["label"].config(text=str(value))

            # Update the OK label
            color = "green" if status else "red"
            text = 'Pass' if status else 'Fail'
            info["ok_label"].config(bg=color, text=text)
         
      # Check if all statuses are True
      if status_list and all(status_list):
         self.Shutdown()
    
   def Shutdown(self):
      self.bq_adapter.device.smb_write_block(commands["BQ40Z50_ADDR"], commands["MFR_BLK_ACC_ADDR"], commands["SHUTDOWN_CMD"])
      time.sleep(0.5)
      self.bq_adapter.device.smb_write_block(commands["BQ40Z50_ADDR"], commands["MFR_BLK_ACC_ADDR"], commands["SHUTDOWN_CMD"])
      
   def __init__(self, master, *args, **kwargs):
      ttk.Frame.__init__(self,master, *args, **kwargs)
      
      self.bq_adapter = None
      
      #create frames
      frame_t = ttk.LabelFrame(self, height=70,padx=5,pady=5)
      frame_t.pack(side=ttk.TOP)
      
      frame_b = ttk.LabelFrame(self,padx=5,pady=5)
      frame_b.pack(side=ttk.BOTTOM, fill="both", expand=True)

      frame_l = ttk.LabelFrame(frame_b, bd=5, bg="light gray",padx=5,pady=5)
      frame_l.pack(side=ttk.LEFT, fill="both", expand=True)

      frame_r = ttk.LabelFrame(frame_b, bd=5, bg="white",padx=5,pady=5)
      frame_r.pack(side=ttk.RIGHT, fill="both", expand=True)
      
      
      ttk.Label(frame_t, text="Battery Shutdown Tool", fg="black", font=("Arial", 15, "bold")).grid(row=0, column=0,pady=10,padx=10)
      
      ttk.Label(frame_l, text="Connection Status", font=("Calibri", 12, "bold"),bg="light gray").grid(row=0, column=0,sticky=W,padx=10,pady=10)
      
      ttk.Label(frame_l, text="Adapter", font=("Calibri", 12),bg="light gray").grid(row=1, column=0, sticky=W, padx=10)
      self.info1 = ttk.Label(frame_l, text='Disconnected', font=("Calibri", 12),bg="light gray")
      self.info1.grid(row=1,column=1, sticky=W, padx=10)
      
      ttk.Label(frame_l, text="Battery", font=("Calibri", 12),bg="light gray").grid(row=2, column=0, sticky=W, padx=10)
      self.info2 = ttk.Label(frame_l, text='Disconnected', font=("Calibri", 12),bg="light gray")
      self.info2.grid(row=2,column=1, sticky=W, padx=10)
      
      ttk.Label(frame_l, text="Device Name", font=("Calibri", 12, "bold"),bg="light gray").grid(row=3, column=0,sticky=W,padx=10,pady=10)
      self.info3 = ttk.Label(frame_l, text='Disconnected', font=("Calibri", 12),bg="light gray")
      self.info3.grid(row=3,column=1, sticky=W, padx=10)
      

      ttk.Label(frame_r, text="Test Values", font=("Calibri", 12, "bold"),  bg="white").grid(row=0, column=0,pady=10, sticky=E)

      
      i=0
      for  parameter, info in checks.items():
         ttk.Label(frame_r,text=parameter, font=("Calibri", 12), bg="white").grid(row=i+1,column=0, sticky=W, padx=20, pady=5)
         info["label"]=ttk.Label(frame_r, text= 0, font=("Calibri", 12), bg="white")
         info["label"].grid(row=i+1, column=1, sticky=W, padx=20, pady=5)
         info["ok_label"]=ttk.Label(frame_r, text= "Check", font=("Calibri", 12), bg="light gray")
         info["ok_label"].grid(row=i+1, column=2, sticky=W, padx=20, pady=5)
         i+=1

      ttk.Button(frame_r, text="Start", command = self.CheckValues, font=("Calibri", 15),padx=5).grid(row=i+6,column=0,pady=30, sticky=E)
      self.CheckAdapter()
      
        
if __name__ == "__main__":
   root = ttk.Tk()
   root.title('Battery Shutdown Tool V3.0')
   MainApplication(root).pack(side="top", fill="both", expand=True)
   root.mainloop()
   