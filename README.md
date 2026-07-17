# AIMS
The aim of this project was to understand the biodiversity impacts and greenhouse gas impacts of production of food in the wholesale market monitored by Mandala, before and after the introduction of the redistribution hub. 

This program maps the greenhouse gas impacts and biodiversity impacts per kg of given food produced in the UK to the products and weights reported from Mandala and TAWS, to give the greenhouse gas impacts and biodiversity impacts of that redistributed produce item. 

# METHOD
This program maps the greenhouse gas impacts and biodiversity impacts per kg of given food produced in the UK, as found in impacts_aggregated_GBR, to the products and weights reported in Mandala_inflow_data, Mandala_outflow_data, and TAWS_quantitative_surplus_data. 

It does this by using the article_item_corpus to train a simple heuristic model to accurately match different food items (including spelling mistakes) to the available ones in the environmental impacts dataset, increasing accuracy of matches from 40% to over 90%. In addition, this should hopefully allow for increased future extensibility and help reduce manual sorting time. 

# INPUTS AND OUTPUTS
Requires an input and an output folder in the same folder to work.

input should contain:
* BWM_waste.csv
* impacts_aggregated_GBR.csv
* Mandala_inflow_data.csv
* Mandala_outflow_data.csv
* TAWS_quantitative_surplus_data.csv

output will contain:
* Mandala_in_output.csv - equivalent to Mandala_inflow_data with greenhouse gas and biodiversity impacts appended
* Mandala_out_output.csv - equivalent to Mandala_outflow_data with greenhouse gas and biodiversity impacts appended
* TAWS_output.csv - equivalent to TAWS_quantitative_surplus with greenhouse gas and biodiversity impacts appended
* month.csv - greenhouse gas and biodiversity impacts grouped by month
* dest.csv - greenhouse gas and biodiversity impacts grouped by destination
* month_dest.csv - greenhouse gas and biodiversity impacts grouped by destination by month
* waste_vs_redistributed.csv - weight of all produce that went to waste and weight of all produce that was redistributed, grouped by month. 
* graphs - a folder containing graphs that correspond with month, dest, month_dest and waste_vs_redistributed

## GRAPHS
* month_ghg_total: total greenhouse gas impacts per month from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in month.csv.

* month_ghg_mean: mean greenhouse gas impacts per kg of produce per month from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in month.csv.

* month_bd_opp: approximate total biodiversity impacts per month (with error margin) from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in month.csv.

* destination_ghg_total: total greenhouse gas impacts per destination from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in dest.csv.

* destination_ghg_mean: mean greenhouse gas impacts per kg of produce per destination from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in dest.csv.

* destination_bd_opp: approximate total biodiversity impacts per destination (with error margin) from production of food that was recorded in the wholesale market by Mandala and TAWS in the months April 2024 - March 2026. The data for this graph is found in dest.csv.

* mandala_dest_ghg_total: total greenhouse gas impacts per destination per month from production of food that was recorded in the wholesale market by Mandala in the months April 2025 - August 2025. The data for this graph is found in month_dest.csv.

* mandala_dest_ghg_mean: mean greenhouse gas impacts per kg of produce per destination per month from production of food that was recorded in the wholesale market by Mandala in the months April 2025 - August 2025. The data for this graph is found in month_dest.csv.

* waste_vs_redistribution: total mass of organic waste per month recorded by BWM in the market between January 2021 and Feburary 2026 compared to total mass of redistributed produce per month recorded by Mandala and TAWS between April 2024 and March 2026. The data for this graph is found in waste_vs_redistribution.csv.
