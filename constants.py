from datetime import datetime

commands={"BQ40Z50_ADDR": 0x17,
         "DEVICE_CMD" : 0x21,
         "MFGDATE_CMD" : 0x1B,
         "VOLT_CMD" : 0x09,
         "TEMP_CMD" : 0x08,
         "CURR_CMD" : 0x0A,
         "MAXE_CMD" : 0x0C,
         "RSOC_CMD" : 0x0D,
         "RCAP_CMD" : 0x0F,
         "CCNT_CMD" : 0x17,
         "SN_CMD" : 0x1C,
         "FCC_CMD" : 0x10,
         "SHUTDOWN_CMD" : [0x10,0x00],
         "MFR_BLK_ACC_ADDR" : 0x44
          }

device_limits = {
         "958231": {"Voltage [mV]": (8000, 12300), "Current [mA]": 0,"Temperature [\u2103]": (10, 40), "Max error [%]": (0, 2), "State of charge [%]": (5, 30), "Remaining capacity [mAh]":(500, 3000),"Cycle count": (0,5),"Full charge capacity [mAh]": 5820, "Serial number": 4, "Manufacturer date": 2},
         "453564918601": {"Voltage [mV]": (8000, 12300), "Current [mA]": 0,"Temperature [\u2103]": (10, 40), "Max error [%]": (0, 2), "State of charge [%]": (5, 30), "Remaining capacity [mAh]":(500, 3000),"Cycle count": (0,5),"Full charge capacity [mAh]": 5820, "Serial number": 4, "Manufacturer date": 2}
      }

checks = {
         "Voltage [mV]": { "parameter":'voltage', "cmd": commands["VOLT_CMD"],  "label": 'self.l4', "ok_label": 'self. OKlabel2'},
         "Current [mA]": { "parameter":'current', "cmd": commands["CURR_CMD"],  "label": 'self. l6', "ok_label": 'self. OKlabel3'},
         "Temperature [\u2103]": { "parameter":'temperature', "cmd": commands["TEMP_CMD"],  "label": 'self. l8', "ok_label": 'self. OKlabel4', "scale": 0.1, "constant":-273.15},
         "Max error [%]": { "parameter":'maxerror', "cmd": commands["MAXE_CMD"],  "label": 'self. l10', "ok_label": 'self. OKlabel5'},
         "State of charge [%]": { "parameter":'rsoc', "cmd": commands["RSOC_CMD"],  "label": 'self. l12', "ok_label": 'self. OKlabel6'},
         "Remaining capacity [mAh]": { "parameter":'rcap', "cmd": commands["RCAP_CMD"],  "label": 'self. l14', "ok_label": 'self. OKlabel7'},
         "Cycle count": { "parameter":'cyclecount', "cmd": commands["CCNT_CMD"],  "label": 'self. 16', "ok_label": 'self. OKlabel8'},
         "Full charge capacity [mAh]": { "parameter":'fcc', "cmd": commands["FCC_CMD"],  "label": 'self. l18', "ok_label": 'self. OKlabel9', "greater_than": True},
         "Serial number": { "parameter":'serialnumber', "cmd": commands["SN_CMD"],  "label": 'self. l20', "ok_label": 'self. OKlabel10', "greater_than": True},
         "Manufacturer date": { "parameter":'mfgdate', "cmd": commands["MFGDATE_CMD"],  "label": 'self. l22', "ok_label": 'self. OKlabel11', "date_check": True}
         
      }

def decode_date(encoded_date):
   year = encoded_date // 512 + 1980
   month = (encoded_date % 512) // 32
   day = encoded_date % 32
   decoded_date = datetime(year, month, day)
   
   return datetime.date(decoded_date)
