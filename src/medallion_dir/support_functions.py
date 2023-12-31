import pyspark
import pyspark.sql.types as T
import pyspark.sql.functions as F

from pyspark.sql import Row
from random import randint, uniform

from src.attributes_dir import attributes as A
from src.common_dir import common_functions as C

import delta.tables as DT
import pyspark
import json


def _aggregate_reviews(review_scores_rating, review_scores_accuracy, review_scores_cleanliness, review_scores_checkin, review_scores_communication, review_scores_location, review_scores_value) -> float:
    """
    Aggregate all the review scores into one number. This function shows how to create an UDF and use it in a Delta Live Table workflow.

    :param review_scores_rating: How accurate the reviews are. From 1-10.
    :type review_scores_rating: double 
    :param review_scores_accuracy: How accurate the reviews are. From 1-10.
    :type review_scores_accuracy: double 
    :param review_scores_cleanliness: How clean the rental was. From 1-10
    :param review_scores_checkin: How easy the check in was. From 1-10.
    :type review_scores_checkin: double 
    :param review_scores_communication: How well the communication went. From 1-10.
    :type review_scores_communication: double
    :param review_scores_location: Was the rental located in a good area. From 1-10.
    :type review_scores_location: double 
    :param review_scores_value: Was the price applicable for the rental. From 1-10.
    :type review_scores_value: double
    :return: The aggregated number of all the reviews.
    :rtype: float
    """

    aggregated_value = float(review_scores_rating) + float(review_scores_accuracy) + float(review_scores_cleanliness) + float(review_scores_checkin) + float(review_scores_communication) + float(review_scores_location) + float(review_scores_value)

    return float(aggregated_value)

def create_mock_dataset() -> str:
    """This function creates a mock dataset which will be used for testing the medallion component. The function creates the dataset and saves it as a table. 
    
    :return: The name of the table created
    :rtype: str
    """
    
    spark = C.Common.create_spark_session()

    # This dataset will be used to verify the DLT expectations in the bronze layer and the dropna in the silver layer
    random_data = []
    for _ in range(10):
        random_row = Row(
            host_is_superhost=str(randint(0, 1)),
            cancellation_policy=" ",
            instant_bookable=str(randint(0, 1)),
            host_total_listings_count=uniform(1, 10),
            neighbourhood_cleansed=" ",
            latitude=uniform(-90, 90),
            longitude=uniform(-180, 180),
            property_type="Random Property Type",
            room_type="Random Room Type",
            accommodates=uniform(1, 10),
            bathrooms=uniform(1, 5),
            bedrooms=uniform(1, 5),
            beds=uniform(1, 5),
            bed_type="Random Bed Type",
            minimum_nights=randint(1, 10),
            number_of_reviews=randint(0, 100),
            review_scores_rating=uniform(0, 100),
            review_scores_accuracy=uniform(0, 10),
            review_scores_cleanliness=uniform(0, 10),
            review_scores_checkin=uniform(0, 10),
            review_scores_communication=uniform(0, 10),
            review_scores_location=uniform(0, 10),
            review_scores_value=uniform(0, 10),
            price=uniform(10, 100)
        )
        random_data.append(random_row)

    # Convert the random data to a DataFrame
    random_df = spark.createDataFrame(random_data)

    #Replace empty string with None value for attribute cancellation_policy
    adding_none_to_random_df = random_df.withColumn(A.AttributesOriginal.cancellation_policy.name, \
        F.when(F.col(A.AttributesOriginal.cancellation_policy.name)==" " ,None) \
            .otherwise(F.col(A.AttributesOriginal.cancellation_policy.name)))
    
    # This row is used for verifying the aggregation UDF in the gold layer
    random_data_2 = []
    for _ in range(1):
        random_row_2 = Row(
            host_is_superhost=str(randint(0, 1)),
            cancellation_policy="Random",
            instant_bookable=str(randint(0, 1)),
            host_total_listings_count=uniform(1, 10),
            neighbourhood_cleansed="Random",
            latitude=uniform(-90, 90),
            longitude=uniform(-180, 180),
            property_type="Random Property Type",
            room_type="Random Room Type",
            accommodates=uniform(1, 10),
            bathrooms=uniform(1, 5),
            bedrooms=uniform(1, 5),
            beds=uniform(1, 5),
            bed_type="Random Bed Type",
            minimum_nights=randint(1, 10),
            number_of_reviews=randint(0, 100),
            review_scores_rating=1,
            review_scores_accuracy=1,
            review_scores_cleanliness=1,
            review_scores_checkin=1,
            review_scores_communication=1,
            review_scores_location=1,
            review_scores_value=1,
            price=uniform(10, 100)
        )
        random_data_2.append(random_row_2)

        random_2_df = spark.createDataFrame(random_data_2)

        # Union of the two random dataframes
        combined_random_df = adding_none_to_random_df.union(random_2_df)

        tbl_nm = "default.test_medallion_combined_random_df"

        combined_random_df.write.format("delta").mode("overwrite").saveAsTable(tbl_nm)

        return tbl_nm
    
    
def _get_dbutils(spark):
    """
    This support function seems to be needed when using dbutils in Nutter testing. Otherwise, is dbutils working without importing.

    :param spark: A spark session
    :type spark: pyspark.sql.session.SparkSession

    :returns: A dbutils instance
    :rtype: dbruntime.dbutils.DBUtils
    """
    try:
        from pyspark.dbutils import DBUtils
        dbutils = DBUtils(spark)
    except ImportError:
        import IPython
        dbutils = IPython.get_ipython().user_ns["dbutils"]
    return dbutils
    
    
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

    spark = C.Common.create_spark_session()

    dbutils = _get_dbutils(spark)

    # Unmount the Blob storage if it's already mounted
    try:
        dbutils.fs.unmount(mount_point)
    except:
        pass

    # Mount the Blob storage
    dbutils.fs.mount(
        source=f"wasbs://{container_name}@{storage_account_name}.blob.core.windows.net",
        mount_point=mount_point,
        extra_configs={
            f"fs.azure.account.key.{storage_account_name}.blob.core.windows.net": storage_account_key
        }
    )

    spark.conf.set("spark.databricks.delta.formatCheck.enabled", "false")


def extract_file_nm_of_last_upsert_fn(test, spark) -> str:
    """
    This function extracts the file name from the bronze table of the last upsert.

    :param test: A variable that is either a empty string or holding the string "test_"
    :type test: str

    :param spark: A spark session
    :type spark: pyspark.sql.session.SparkSession

    :returns: The name of the file from the last upsert
    :rtype: str
    """
        
    try:
        bronze_df = spark.table(f"default.{test}adls_bronze_layer")

        last_read_input_file_str = bronze_df.sort(F.col("input_file_name"), ascending=False).select(F.col("input_file_name")).first()[0]

        return last_read_input_file_str
    
    except:
        return None


def file_exists_fn(last_read_input_file_str, test) -> bool:
    """
    This function checks if there is a new file to read from the Azure Data Lake Storage. 

    :param last_read_input_file_str: A file name of the last upsert
    :type last_read_input_file_str: str

    :param test: A variable that is either a empty string or holding the string "test_"
    :type test: str

    :returns: A boolean value
    :rtype: bool
    """

    substring = last_read_input_file_str.split("/")[-1].split(".")[0]
    file_version = substring.split(f"{test}airbnb_")[1]

    try:
        dbutils.fs.ls(f"dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version) + 1)}.csv")
        return True
    except:
        print(f"There exists no new files to read from Azure Data Lake Storage. The last file that was inserted was: " 
              f"'dbfs:/mnt/azure_data_lake/airbnb/{test}airbnb_{str(int(file_version))}.csv")
        return False
    
    
def read_new_data_fn(last_read_input_file_str, test, spark) -> pyspark.sql.dataframe.DataFrame:
    """
    This reads the new data from file from the mounted Azure Data Lake Storage. 

    :param last_read_input_file_str: A file name of the last upsert
    :type last_read_input_file_str: str

    :param test: A variable that is either a empty string or holding the string "test_"
    :type test: str

    :param spark: A spark session
    :type spark: pyspark.sql.session.SparkSession

    :returns: A boolean value
    :rtype: bool
    """

    substring = last_read_input_file_str.split("/")[-1].split(".")[0]
    file_version = substring.split(f"{test}airbnb_")[1]

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
    

def mount_path_exists_fn(mnt_path, spark) -> bool:
    """
    This function checks if there is a valid file path to read from the Azure Data Lake Storage. 

    :param mnt_path: The path to the mounted folder in Databricks
    :type mnt_path: str

    :param spark: A spark session
    :type spark: pyspark.sql.session.SparkSession

    :returns: A boolean value
    :rtype: bool
    """

    dbutils = _get_dbutils(spark)

    try:
        dbutils.fs.ls(mnt_path)
        return True
    except:
        return False