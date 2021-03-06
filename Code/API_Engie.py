# LIBRARY IMPORTATION
from flask import Flask, render_template, request, jsonify
import json
import pandas as pd

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

@app.route('/')
def Welcoming_text():
   return "Welcome to the Engie Challenge API - Please go to this link : http://localhost:8888/productionplan"

@app.route('/productionplan')
def upload_file():
   return render_template('index.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def uploader_file():
   if request.method == 'POST':
      f = request.files['file']
      payload = json.load(f)

      # Function to calculate the cost per MWh
      def function_cost_1MWh(x):
         if x['type'] == "gasfired":
            return round((gas_euro_MWh * (1 / x["efficiency"])) +  (0.3 * co2_euro_ton),2)
         elif x['type'] == "turbojet":
            return round(kerosine_euro_MWh * (1 / x["efficiency"]),2) # Do we need to add the C02 ?
         elif x['type'] == 'windturbine':
            return 0

      # Convert the Json File to a panda tab
      df_powerplants = pd.DataFrame.from_dict(payload["powerplants"])

      # Extraction of important value
      gas_euro_MWh = payload["fuels"]["gas(euro/MWh)"]
      kerosine_euro_MWh = payload["fuels"]["kerosine(euro/MWh)"]
      co2_euro_ton = payload["fuels"]["co2(euro/ton)"]
      wind_percentage = payload["fuels"]["wind(%)"]
      load_max  = payload["load"]

      # Calculation of 1MWh and pmax for the windturbine(considering wind%)
      df_powerplants["cost_1MWh"] = df_powerplants.apply(function_cost_1MWh, axis =1)

      for index, row in df_powerplants.iterrows():
         if row["type"] == "windturbine":
            df_powerplants.at[index , "pmax"] = round(row["pmax"] * (wind_percentage/100),1)

      # Creation of two new columns to fill in later
      df_powerplants["load"] = load_max
      df_powerplants["p"] = 0

      # Reset the Index reset to have the less expensive methods in the first row
      df_powerplants = df_powerplants.sort_values('cost_1MWh').reset_index() # Should I add pmin ?
      df_powerplants.drop('index', inplace=True, axis=1)

      #The main idea here is to work only on all the row where load is superior to the cumul of pmax plus one row.
      #On this rows, the pmin is set on the p.
      load_remain = load_max
      df_powerplants["pmax_cumul"] = df_powerplants["pmax"].cumsum()
      for index, row in df_powerplants.iterrows():
         if load_remain >  0 :
            df_powerplants.at[index , "p"] = row["pmin"]
            load_remain -= row["pmax"]

      # Like the p have been set on pmin on some row, we create a new variable updated without the p.
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

      # Calculate the total cost of each powerplants
      df_powerplants["total_cost"] = df_powerplants.apply(lambda x: round(x["p"] * x["cost_1MWh"],2), axis = 1)

      # Create a dictionnary and return it in json
      result = df_powerplants[["name", "p", "total_cost"]].to_dict('records')
      return jsonify(result)

@app.errorhandler(500)
def file_error(error):
    return 'File is missing or Wrong format file or wrong structure (See "exemple.payload.json" on GitHub)', 500

@app.errorhandler(404)
def page_not_found(error):
    return 'This page does not exist. Please enter : http://127.0.0.1:8888/productionplan ', 404

if __name__ == '__main__':
    app.run(debug = False, port=8888)
