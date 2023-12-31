# Databricks notebook source
# MAGIC %md
# MAGIC # Set up a connection to ADLS

# COMMAND ----------

"""
Note that I am reading from a txt file that holds my secrets. This file is not pushed to GitHub since I have added it to gitignore. Please note that this is not the best way of storing secrets but is a work around for now since I do not have admin rights to create an Azure Key Vault. 
"""

# importing the module
import json
  
# reading the data from the file
with open('/Workspace/Repos/andreas.forsberg@capgemini.com/mvp_ml_delivery-main/authorization_adls.txt') as f:
    data = f.read()
      
# reconstructing the data as a dictionary
authorization_dct = json.loads(data)

# COMMAND ----------

spark.conf.set(f"fs.azure.account.key.{authorization_dct['storage_account_name']}.dfs.core.windows.net", authorization_dct['key'] )

# COMMAND ----------

dbutils.fs.ls("abfss://airbnb@anforsbeadlsgen2.dfs.core.windows.net/")

# COMMAND ----------

df = (spark.read
  .format("csv")
  .option("sep", ",")
  .option("header", True)
  .load("abfss://airbnb@anforsbeadlsgen2.dfs.core.windows.net/airbnb.csv")
)

# COMMAND ----------

df.display()

# COMMAND ----------

# MAGIC %md
# MAGIC # Mount ADLS
# MAGIC Try this and then repeat below 

# COMMAND ----------

from src.common_dir.common_functions import Common
import pyspark.sql.functions as F
import pyspark.sql.types as T
import delta.tables as DT
import pyspark
import json

# COMMAND ----------

def mount_to_adls_fn() -> None:

    """
    Note that I am reading from a txt file that holds my secrets. This file is not pushed to GitHub since I have added it to gitignore. Please note that this is not the best way of storing secrets but is a work around for now since I do not have admin rights to create an Azure Key Vault. 
    """
    
    # Reading the data from the file
    with open('/Workspace/Repos/andreas.forsberg@capgemini.com/mvp_ml_delivery-main/authorization_adls.txt') as f:
        data = f.read()
        
    # Reconstructing the data as a dictionary
    authorization_dct = json.loads(data)

    # Code from ChatGPT
    storage_account_name = authorization_dct["storage_account_name"]
    storage_account_key = authorization_dct["key"] 
    container_name = "airbnb"
    mount_point = "/mnt/azure_data_lake/airbnb"

    # Unmount the Blob storage if it's already mounted*
    # Comment out if it is the first time mounting
    dbutils.fs.unmount(mount_point)

    # Mount the Blob storage
    dbutils.fs.mount(
        source=f"wasbs://{container_name}@{storage_account_name}.blob.core.windows.net",
        mount_point=mount_point,
        extra_configs={
            f"fs.azure.account.key.{storage_account_name}.blob.core.windows.net": storage_account_key
        }
    )

    spark.conf.set("spark.databricks.delta.formatCheck.enabled", "false")

# COMMAND ----------

"""
Note that I am reading from a txt file that holds my secrets. This file is not pushed to GitHub since I have added it to gitignore. Please note that this is not the best way of storing secrets but is a work around for now since I do not have admin rights to create an Azure Key Vault. 
"""

# Importing the module
import json
  
# Reading the data from the file
with open('/Workspace/Repos/andreas.forsberg@capgemini.com/mvp_ml_delivery-main/authorization_adls.txt') as f:
    data = f.read()
      
# Reconstructing the data as a dictionary
authorization_dct = json.loads(data)

# COMMAND ----------

# Code from ChatGPT

storage_account_name = authorization_dct["storage_account_name"]
storage_account_key = authorization_dct["key"] 
container_name = "airbnb"
mount_point = "/mnt/azure_data_lake/airbnb"

# Unmount the Blob storage if it's already mounted*
# Comment out if it is the first time mounting
dbutils.fs.unmount(mount_point)

# Mount the Blob storage
dbutils.fs.mount(
    source=f"wasbs://{container_name}@{storage_account_name}.blob.core.windows.net",
    mount_point=mount_point,
    extra_configs={
        f"fs.azure.account.key.{storage_account_name}.blob.core.windows.net": storage_account_key
    }
)

# COMMAND ----------

spark.conf.set("spark.databricks.delta.formatCheck.enabled", "false")

# COMMAND ----------

df = (spark.read
  .format("csv")
  .option("sep", ",")
  .option("header", True)
  .load("dbfs:/mnt/azure_data_lake/airbnb/airbnb_1.csv")
)

# COMMAND ----------

df.display()

# COMMAND ----------

test_mode = "true"

# One can not set a boolan value as a task value in jobs, only strings
#if test_mode == "true":
#    test_mode = True

# COMMAND ----------

type(test_mode)

# COMMAND ----------

def extract_file_nm_of_last_upsert_fn(test_mode) -> str:
    """
    This function extracts the file name from the bronze table of the last upsert.

    :param bronze_df: The validation data
    :type bronze_df: pyspark.sql.dataframe.DataFrame

    :returns: The name of the file from the last upsert
    :rtype: str
    """

    test = ""

    if test_mode:
        test = "test_"
        
    try:
        bronze_df = spark.table(f"default.{test}adls_bronze_layer")

        last_read_input_file_str = bronze_df.sort(F.col("input_file_name"), ascending=False).select(F.col("input_file_name")).first()[0]

        return last_read_input_file_str
    
    except:
        return None

# COMMAND ----------

def file_exists_fn(last_read_input_file_str, test_mode) -> bool:
    """
    This function checks if there is a new file to read from the Azure Data Lake Storage. 

    :param last_read_input_file_str: A file name of the last upsert
    :type last_read_input_file_str: str

    :returns: A boolean value
    :rtype: bool
    """

    test = ""

    if test_mode:
        test = "test_"

    substring = last_read_input_file_str.split("/")[-1].split(".")[0]
    file_version = substring.split(f"{test}airbnb_")[1]

    try:
        dbutils.fs.ls(f"dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version) + 1)}.csv")
        return True
    except:
        print(f"There exists no new files to read from Azure Data Lake Storage. The last file that was inserted was: " 
              f"'dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version))}.csv")
        return False

# COMMAND ----------

def read_new_data_fn(last_read_input_file_str, test_mode) -> pyspark.sql.dataframe.DataFrame:
    """
    This reads the new data from file from the mounted Azure Data Lake Storage. 

    :param last_read_input_file_str: A file name of the last upsert
    :type last_read_input_file_str: str

    :returns: A boolean value
    :rtype: bool
    """

    test = ""

    if test_mode:
        test = "test_"

    substring = last_read_input_file_str.split("/")[-1].split(".")[0]
    print("substring", substring)
    file_version = substring.split(f"{test}airbnb_")[1]

    print("In read_new_data_fn file_version", file_version)

    print("In read_new_data_fn file_version + 1", str(int(file_version) + 1))

    try:
        df = (spark.read
            .format("csv")
            .option("sep", ",")
            .option("header", True)
            .load(f"dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version) + 1)}.csv")
            )
    
        # Add a column with the file name of the incoming file
        df_temp = df.withColumn("input_file_name", F.input_file_name())
        
        df_temp.write.format("delta").mode("overwrite").saveAsTable("default.temp_adls_bronze_layer")
        
        return df_temp
    except:
        print(f"There exists no new files to read from Azure Data Lake Storage. The last file that was inserted was: " 
              f"'dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version))}.csv")
        
        empty_df = spark.createDataFrame([], schema=T.StructType([]))
        
        return empty_df

# COMMAND ----------

def mount_path_exists_fn(mnt_path) -> bool:
    """
    This function checks if there is a valid file path to read from the Azure Data Lake Storage. 

    :param mnt_path: The path to the mounted folder in Databricks
    :type mnt_path: str

    :returns: A boolean value
    :rtype: bool
    """

    try:
        dbutils.fs.ls(mnt_path)
        return True
    except:
        return False

# COMMAND ----------

mount_path_exists_fn("dbfs:/mnt/azure_data_lake/airbnb/airbnb_1.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Merge into bronze

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP TABLE default.test_adls_bronze_layer

# COMMAND ----------

# MAGIC %sql
# MAGIC DROP TABLE default.adls_bronze_layer

# COMMAND ----------

def read_adls_merge_into_bronze(mnt_path: str, test_mode: bool) -> None:

    """
    Applies merge into for data read from Azure Data Lake Storage. Merge into updates the row if the join condition already exists and inserts a new row if it does not.

    :param mnt_path: The path where data read from Azure Data Lake Storage can be accessed. Should refer to the first file.
    :type mnt_path: str

    :param test_mode: Indicated if test mode should be running or not
    :type test_mode: bool
    """

    if not mount_path_exists_fn(mnt_path):
        raise FileNotFoundError(f"Please check that you provided a valid path to the first file (e.g. airbnb_1) in the mounted folder located in DBFS")
    
    # To break the loop if no matching file initially can not be found
    initial_trial_counter = 0

    while True:

        initial_trial_counter +=1
        if initial_trial_counter > 2:
            break

        test = ""

        if test_mode:
            test = "test_"

        #Create SparkSession, needed when using repos. 
        spark = Common.create_spark_session()

        # Extract file name of the last upsert
        last_read_input_file_str = extract_file_nm_of_last_upsert_fn(test_mode)

        print("last_read_input_file_str", last_read_input_file_str)

        print('spark.catalog.tableExists("default.test_adls_bronze_layer"): ', spark.catalog.tableExists(f"default.{test}adls_bronze_layer"))

        # If there is no input file or an already existing table, then create a table from the path from mounting folder
        if last_read_input_file_str is None or spark.catalog.tableExists(f"default.{test}adls_bronze_layer") is not True:
        
            df = (spark.read
                .format("csv")
                .option("sep", ",")
                .option("header", True)
                .load(mnt_path)
                )
            
            # Add a column with the file name of the incoming file
            df_new = df.withColumn("input_file_name", F.input_file_name())
            
            df_new.write.format("delta").mode("overwrite").saveAsTable(f"default.{test}adls_bronze_layer")
        
        else:

            # Then check if there is a new file name to read from Azure Data Lake Storage and merge

            # Extract file name of the last upsert
            last_read_input_file_str = extract_file_nm_of_last_upsert_fn(test_mode)

            new_data_df = read_new_data_fn(last_read_input_file_str, test_mode)

            # To break the while loop
            if new_data_df.isEmpty():
                break

            tbl=DT.DeltaTable.forName(spark, tableOrViewName=f"default.{test}adls_bronze_layer")
            
            # Very unlikely for two rows to have the same longitude and latitude
            join_cond = "original.longitude = updates.longitude and original.latitude = updates.latitude"
            col_dct={}

            for col in new_data_df.columns:
                col_dct[f"{col}"]=f"updates.{col}"

            tbl.alias("original").merge(new_data_df.alias("updates"),join_cond)\
            .whenMatchedUpdate(set=col_dct)\
            .whenNotMatchedInsert(values=col_dct)\
            .execute()


# COMMAND ----------

read_adls_merge_into_bronze(mnt_path="dbfs:/mnt/azure_data_lake/airbnb/airbnb_1.csv", test_mode = False)

# COMMAND ----------

adls_df = spark.table("default.adls_bronze_layer")

# COMMAND ----------

adls_df.display()

# COMMAND ----------

df = spark.table("dlt.gold_dlt_table")

# COMMAND ----------

df.display()

# COMMAND ----------

# MAGIC %md
# MAGIC # Set up a connection with autolaoder
# MAGIC It doers not work. Most likely do I need extra configurations which i dont have access to. See the Advancing Spark YouTube video 

# COMMAND ----------

spark.conf.set("spark.databricks.delta.formatCheck.enabled", "false")

# COMMAND ----------

def autoload_to_table(data_source, source_format, table_name, checkpoint_directory):
    (spark.readStream
             .format("cloudFiles")
             .option("cloudFiles.format", source_format)
             .option("cloudFiles.schemaLocation", checkpoint_directory)
             .load(data_source)
    )

# COMMAND ----------

autoload_to_table(data_source="dbfs:/mnt/azure_data_lake/airbnb/airbnb_1.csv", source_format="csv", table_name="autoloader_airbnb", checkpoint_directory="/dbfs/FileStore/Autoloader/REMOVE")

# COMMAND ----------

"""
(spark.readStream
             .format("cloudFiles")
             .option("cloudFiles.format", source_format)
             .option("cloudFiles.schemaLocation", checkpoint_directory)
             .load(data_source)
             .writeStream
             .option("checkpointLocation", checkpoint_directory)
             .option("mergeSchema", "true")
             .table(table_name)
    )
"""

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

schema = df.schema

# COMMAND ----------

schema

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

test_df = spark.table("default.test_medallion_combined_random_df")

# COMMAND ----------

test_df.display()

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

from src.common_dir import common_functions as C
spark = C.Common.create_spark_session()

# COMMAND ----------

type(spark)

# COMMAND ----------

type(dbutils)

# COMMAND ----------

test_mode = True

# COMMAND ----------

test = ""

if test_mode:
    test = "test_"

# COMMAND ----------

spark.table(f"default.{test}adls_bronze_layer")

# COMMAND ----------

counter = 0
while True:
    counter += 1
    print(counter)
    if counter > 5:
        if counter > 3: 
            break

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

def REMOVE(self, mnt_path, fraction, seed, test_mode) -> S.dataframe.DataFrame:

        """
        Applies merge into for data read from Azure Data Lake Storage. Merge into updates the row if the join condition already exists and inserts a new row if it does not.

        :param mnt_path: The path where data read from Azure Data Lake Storage can be accessed. Should refer to the first file in the order you want to read.
        :type mnt_path: str

        :param fraction: The fraction the data should be sampled into. Use 1.0 for full dataset. 
        :type fraction: float

        :param seed: The seed parameter of the sample function. 
        :type seed: in

        :param test_mode: A boolean value to indicate if test mode should be running
        :type test_mode: bool

        :return: A spark dataframe with bronze data
        :rtype: S.dataframe.DataFrame
        """

        #Create SparkSession, needed when using repos. 
        spark = C.Common.create_spark_session()

        test = ""

        if test_mode:
            test = "test_"

            # Drop the table "default.airbnb"
            spark.sql(f"DROP TABLE default.{test}adls_bronze_layer")

        # Mount to Azure Data Lake Storage
        SF.mount_to_adls_fn()

        # Extract file name of the last upsert
        last_read_input_file_str = SF.extract_file_nm_of_last_upsert_fn(test_mode)

        print("last_read_input_file_str", last_read_input_file_str)

        # If there is no input file or an already existing table, then create a table from the path from mounting folder
        if last_read_input_file_str is None or spark.catalog.tableExists(f"default.{test}adls_bronze_layer") is not True:
        
            df = (spark.read
                .format("csv")
                .option("sep", ",")
                .option("header", True)
                .load(mnt_path)
                )
            
            # Add a column with the file name of the incoming file
            df_new = df.withColumn("input_file_name", F.input_file_name())
            
            df_new.write.format("delta").mode("overwrite").saveAsTable(f"default.{test}adls_bronze_layer")

            print("Created the first bronze layer")

        else:

            print("STEP 1")

            # Then check if there is a new file name to read from Azure Data Lake Storage and merge
            # Using a while loop to merge all incomming files
            while SF.file_exists_fn(last_read_input_file_str, test_mode):

                print("DO WE REACH THIS POINT!!!!!!?")

                # Extract file name of the last upsert
                last_read_input_file_str = SF.extract_file_nm_of_last_upsert_fn(test_mode)

                print("last_read_input_file_str", last_read_input_file_str)

                new_data_df = SF.read_new_data_fn(last_read_input_file_str, test_mode)

                # To break the while loop
                if new_data_df.isEmpty():
                    break

                tbl=DT.DeltaTable.forName(spark, tableOrViewName=f"default.{test}adls_bronze_layer")
                
                # Very unlikely for two rows to have the same longitude and latitude
                join_cond = "original.longitude = updates.longitude and original.latitude = updates.latitude"
                col_dct={}

                for col in new_data_df.columns:
                    col_dct[f"{col}"]=f"updates.{col}"

                tbl.alias("original").merge(new_data_df.alias("updates"),join_cond)\
                .whenMatchedUpdate(set=col_dct)\
                .whenNotMatchedInsert(values=col_dct)\
                .execute()
        
        bronze_df = spark.table(f"default.{test}adls_bronze_layer")
        bronze_df = bronze_df.sample(fraction=fraction, seed=seed)

        return bronze_df

# COMMAND ----------



# COMMAND ----------



# COMMAND ----------

bronze_df = spark.table("default.bronze_df_backup_remove")

# COMMAND ----------

bronze_df.display()

# COMMAND ----------

bronze_df.select("host_is_superhost").show(1, truncate=False)

# COMMAND ----------

bronze_df.write.format("delta").mode("overwrite").saveAsTable(f"default.airbnb")

# COMMAND ----------


