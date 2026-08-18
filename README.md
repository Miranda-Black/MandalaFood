# Contents:
* Aims
* Results
* Methods
* Inputs and outputs

# Aims
The aim of this project was to understand the biodiversity and greenhouse gas impacts of production of food passing through the TAWS food surplus redistribution hub. 

We are able to assess the greenhouse gas and biodiversity impacts associated with different food items at the point of their production, which allows us to track the total impact of food passing through the redistribution hub, as well as the split of impacts being diverted to each final destination. It is important to note that food was otherwise destined to be disposed of, so any impacts diverted away from this fate can be considered a good thing. By moving food from waste to redistribution, its production impacts are effectively ‘valorised’. 


# Results
Figure 1. Total monthly greenhouse gas emissions associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in month.csv.

Figure 2. Mean monthly greenhouse gas emissions per kilogram of produce associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in month.csv.

Figure 3. Total monthly water usage associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in month.csv.

Figure 4. Mean monthly water usage per kilogram of produce associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in month.csv.

Figure 5. Mean total biodiversity impact per month associated with the production of food recorded passing through the wholesale market re-distribution hub each month between April 2024 and March 2026. The biodiversity impact metric used is the Land-cover Impacts on Future Extinctions metric, which tracks the elevated extinction risk of ~31000 terrestrial vertebrates associated with continued land-use for food production, and which has units of mean change in extinction probability per species. 

Figure 6A. Total greenhouse gas emissions per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 6B. Total greenhouse gas emissions per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 7A. Mean greenhouse gas emissions per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 7B. Mean greenhouse gas emissions per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 
Figure 8A. Total water usage per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 8B. Total water usage per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 9A. Mean water usage per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 9B. Mean water usage per destination associated with the production of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data underlying this figure can be found in dest.csv. 

Figure 10A. Mean total biodiversity impact per destination associated with the production of food recorded passing through the wholesale market re-distribution hub each month between April 2024 and March 2026. The biodiversity impact metric used is the Land-cover Impacts on Future Extinctions metric, which tracks the elevated extinction risk of ~31000 terrestrial vertebrates associated with continued land-use for food production, and which has units of mean change in extinction probability per species. 

Figure 10B. Mean total biodiversity impact per destination associated with the production of food recorded passing through the wholesale market re-distribution hub each month between April 2024 and March 2026. The biodiversity impact metric used is the Land-cover Impacts on Future Extinctions metric, which tracks the elevated extinction risk of ~31000 terrestrial vertebrates associated with continued land-use for food production, and which has units of mean change in extinction probability per species. 

Figure 11A. Total monthly greenhouse gas emissions per destination associated with the production of food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in month_dest.csv.

Figure 11B. Total monthly greenhouse gas emissions per aggregated destination associated with the production of food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in month_dest.csv.

Figure 12A. Mean monthly greenhouse gas emissions per destination associated with the production of food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in month_dest.csv.

Figure 12B. Mean monthly greenhouse gas emissions per aggregated destination associated with the production of food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in month_dest.csv.

Figure 13. Total monthly mass of organic food waste recorded by Birmingham Wholesale Market between January 2021 and Februrary 2026 compared to the total monthly mass of food recorded by Mandala and TAWS passing through the redistribution hub between April 2024 and March 2026. The data for this graph is found in waste_vs_redistribution.csv.

Figure 14A. Total monthly mass of offered, accepted and redistributed food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in mandala_weights.csv. 

Figure 14B. Percentage monthly mass of rejected, accepted and redistributed food offered to the redistribution hub recorded by Mandala between April 2025 and August 2025. The data underlying this figure can be found in mandala_weights.csv. 

Figure 15. Total mass of each food group compared with its extinction opportunity cost distribution for the food recorded by Mandala passing through the redistribution hub between April 2025 and August 2025. The data underlying this figure can be found in bygroup.csv.

# Method
This program maps the greenhouse gas impacts and biodiversity impacts per kg of given food produced in the UK, as found in impacts_aggregated_GBR, to the products and weights reported in Mandala_inflow_data, Mandala_outflow_data, and TAWS_quantitative_surplus_data. 

It does this by using the article_item_corpus to train a simple heuristic model to accurately match different food items (including spelling mistakes) to the available ones in the environmental impacts dataset, increasing accuracy of matches from 40% to over 90%. In addition, this should hopefully allow for increased future extensibility and help reduce manual sorting time. 

# Inputs and Outputs
Requires an input and an output folder in the same folder to work.

input should contain:
* BWM_waste.csv
* commodity_crosswalk.csv (can be found here: https://github.com/thomasball42/bd_leakage_ratios/blob/main/data/commodity_crosswalk.csv)
* group_quartile_impacts.csv (can be calculated from here: https://github.com/thomasball42/Quantifying-the-impact-of-food-we-eat-on-species-extinctions)
* impacts_aggregated_GBR.csv (can be calculated from here: https://github.com/thomasball42/mrio_pipeline)
* Mandala_inflow_data.csv
* Mandala_outflow_data.csv
* TAWS_quantitative_surplus_data.csv

output will contain:
* Mandala_in_output.csv - equivalent to Mandala_inflow_data with greenhouse gas and biodiversity impacts appended
* Mandala_out_output.csv - equivalent to Mandala_outflow_data with greenhouse gas and biodiversity impacts appended
* TAWS_output.csv - equivalent to TAWS_quantitative_surplus with greenhouse gas and biodiversity impacts appended
* month.csv - water usage, greenhouse gas and biodiversity impacts grouped by month
* dest.csv - water usage, greenhouse gas and biodiversity impacts grouped by destination
* month_dest.csv - water usage, greenhouse gas and biodiversity impacts grouped by destination by month
* bygroup.csv - lower, median and upper quartile biodiversity impacts and weight grouped by food group
* waste_vs_redistributed.csv - weight of all produce that went to waste and weight of all produce that was redistributed, grouped by month.
* mandala_weights.csv - total weight of all produce that was offered, accepted and redistributed, grouped by month
* graphs - a folder containing graphs that correspond with month, dest, month_dest and waste_vs_redistributed

