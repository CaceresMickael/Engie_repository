from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import json
import pandas as pd
from Data_analysis_engie import function_cost_1MWh

app = Flask(__name__)
# app.config[r'C:\Users\MICACERE\Documents\Challenge_Engie']
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
# Function 

@app.route('/productionplan')
def upload_file():
   return render_template('index.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def uploader_file():
   if request.method == 'POST':
      f = request.files['file']
      payload = json.load(f)
      #f.save(secure_filename(f.filename))
      # data_analysis_function(f)
      df_powerplants = pd.DataFrame.from_dict(payload["powerplants"])
      gas_euro_MWh = payload["fuels"]["gas(euro/MWh)"]
      kerosine_euro_MWh = payload["fuels"]["kerosine(euro/MWh)"]
      co2_euro_ton = payload["fuels"]["co2(euro/ton)"]
      wind_percentage = payload["fuels"]["wind(%)"]
      load_max  = payload["load"]
      df_powerplants["cost_1MWh"] = df_powerplants.apply(function_cost_1MWh, axis =1)

      for index, row in df_powerplants.iterrows():
         if row["type"] == "windturbine":
            df_powerplants.at[index , "pmax"] = round(row["pmax"] * (wind_percentage/100),1)

      df_powerplants["load"] = load_max
      df_powerplants["p"] = 0

      df_powerplants = df_powerplants.sort_values('cost_1MWh').reset_index() # Should I add pmin ?
      df_powerplants.drop('index', inplace=True, axis=1)

      load_remain = load_max
      df_powerplants["pmax_cumul"] = df_powerplants["pmax"].cumsum()
      for index, row in df_powerplants.iterrows():
         if load_remain >  0 :
            df_powerplants.at[index , "p"] = row["pmin"]
            load_remain -= row["pmax"]

      load_calculate = load_max - df_powerplants["p"].sum() 
      for index, row in df_powerplants.iterrows():
         #if pmax is superior or equal to the load
         if row["pmax"] <= load_calculate and load_calculate != 0:
            load_calculate -=  row["pmax"] - row["p"]   # Update the load calculate by reducing by pmax and p
            #print("a",index, load_calculate, row["p"], row["pmax"]) # debug checker
            df_powerplants.at[index , "p"] += (row["pmax"] - row["p"] ) # update the p by pmax and take off the actual value
         
         # if pmax superior to the load AND (p + load) superior to pmax
         elif row["pmax"] > load_calculate and (row["p"] + load_calculate) > row["pmax"]:
            df_powerplants.at[index , "p"] =  row["pmax"] # update p by pmax
            load_calculate -=  row["pmax"] - row["p"]
            #print("b",index, load_calculate, row["p"], row["pmax"]) # debug checker
         
         # if pmax is superior to the load AND (p + load) is inferior or equal to pmax
         elif row["pmax"] > load_calculate and (row["p"] + load_calculate) <= row["pmax"] and load_calculate != 0:
            df_powerplants.at[index , "p"] += load_calculate
            load_calculate -=  load_calculate
            #print("c",index, load_calculate, row["p"], row["pmax"]) # debug checker

      df_powerplants["total_cost"] = df_powerplants.apply(lambda x: round(x["p"] * x["cost_1MWh"],2), axis = 1)

      #df_list = df_powerplants.values.tolist() jsonpify(df_list)

      #result = df_powerplants[["name", "p", "total_cost"]].to_json(orient="table", index= False)
      result = df_powerplants[["name", "p", "total_cost"]].to_dict('index')
      return jsonify(result)

#data_analysis_funtion():
   #does stuff

if __name__ == '__main__':
    app.run(debug = False, port=8888)
