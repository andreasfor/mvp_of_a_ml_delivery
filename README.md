# mvp_of_a_ml_deliver
The README file is written more like a diary with a touch of documentation at the moment. Where I can sum up my thoughts and what I have learned.

## Aim of the project
The aim of the project was twofold. First, to try a bunch of methods, tools, approaches, techniques, you name it, that I have come across during my first year as a consultant but perhaps have not had the chance to try until now.
The time cap was roughly three weeks, so I want to emphasize that nothing in this project is exhaustive; it is more of a quick sneak peak.

The second aim of the project was to produce a project that a junior colleague could easily follow so they (count me in) could see what an end-to-end minimal viable product of a machine learning delivery may look like. At the same time, be of sufficient quality to a senior Data Scientist/AI Architect (Jonas Mellin), a senior Data Engineer (Johan Öhman) and a Databricks Champion (Alexander Mafi). The term sufficient here means, if they were to open up this project at a client for the first time, they would say, "OK, maybe not how I would have done it. But, OK" and accept it, rather than chase perfection. In short, for this project, simplicity is rated higher than perfection.   

## What I was trying to build
An ETL flow that reads from an external Azure Data Lake Storage Gen2 using a Databricks function called Autoloader while storing secrets in Azure Key Vault. Once the data is read from the source, it is currated through the medallion structure of bronze to gold. The ETL flow is built with Delta Live Tables (DLT) of which you can easily monitor the health of your incoming data by setting expectations. This ETL flow should be encapsulated by a job, which can be set to a schedule.

In the same job but as another task, should the daily prediction be performed. The gold standard data is sent to the trained machine learning (ML) model, which makes daily predictions. The ML model should have a few requirements. One, it should not brake for new data or if new columns are sent to it. Two, the health of the incoming data and the model should be automatically monitored, and alerts should be sent as soon as a data or model drift occurs. The drifts are monitored with something called Evidently, which is open source. The predictions are saved in a table, and the insights from the table are visualized in a dashboard that updates daily. 

### Requirements
This should be built in Databricks, utilizing testing and a CI/CD approach with three environments (DEV, TEST, PROD), be written in PySpark, and make use of a proper IDE. Visual Studio Code just recently launched a Databricks extension that I wanted to try out. In addition, I wanted to try something called Sphinx and Autodocstring, which are used for documentation. Sphinx produces a searchable web-based interface of your modules and functions, and Autodocstring produces a doc template for each function while coding. Explorative data analysis should be excluded. At least one of the modules should be written with a component oriented approach to show the foundations of how to do it. 

## Thoughts, learnings & what was actually built

If not mentioned otherwise, what was built is what was stated earlier. A blocker for this project was that I was not the administrator of my Visual Studio Professional subscription, which implies that I do not have certain privileges. I will try to get admin rights in order to keep developing the project as intended. This led to several compromises, as will be described below.

### Data
The data used for the project is the AirBnb San Fransisco and the purpose of the ML prediction is to predict the price.

root
 |-- host_is_superhost: string
 |-- cancellation_policy: string
 |-- instant_bookable: string
 |-- host_total_listings_count: double
 |-- neighbourhood_cleansed: string
 |-- latitude: double
 |-- longitude: double
 |-- property_type: string
 |-- room_type: string
 |-- accommodates: double
 |-- bathrooms: double
 |-- bedrooms: double
 |-- beds: double
 |-- bed_type: string
 |-- minimum_nights: long
 |-- number_of_reviews: long
 |-- review_scores_rating: double
 |-- review_scores_accuracy: double
 |-- review_scores_cleanliness: double
 |-- review_scores_checkin: double
 |-- review_scores_communication: double
 |-- review_scores_location: double
 |-- review_scores_value: double
 |-- price: double

### Autoloader and storing secrets in Azure Key Vault

Due to not having admin rights, I could not use Autoloader or Azure Key Vault. The implication of not using Autoloader is a more complex solution where I use an upsert with Merge Into instead and manually keep track of which files have been upserted earlier. Since I could not use Azure Key Vault, I did a poor man's version of it and stored my secrets in a txt file and used gitignore to not push these files.

### ETL Flow
The ETL flow visualized as:

![image](https://github.com/andreasfor/mvp_of_a_ml_delivery/assets/78473680/45fd5fa6-915b-48a4-8eb3-1124356783ab)

Expectations for bronze layer is set to monitor but allow data:

![image](https://github.com/andreasfor/mvp_of_a_ml_delivery/assets/78473680/60ac1b64-7c92-44b3-981e-fdbda380de11)








When this repo is not in private mode one can use this website to get to the documentation [view Sphinx docs](https://htmlpreview.github.io/)




