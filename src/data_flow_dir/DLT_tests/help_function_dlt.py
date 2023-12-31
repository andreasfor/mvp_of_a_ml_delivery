from random import randint, uniform
import pyspark.sql.types as T
import pyspark.sql.functions as F
import pyspark.sql as S

from src.common_dir.common_functions import Common
from src.attributes_dir import attributes as A

#This is only needed for calling spark outside of Databriucks e.g when auto generating documenatation with Sphinx
spark = Common.create_spark_session()

class DLT_Helper:

    # I did not manage to run this helper function as a pytest fixture when running DLT job
    def random_df_str_nm_fn(self) -> str:
        """ 
        :return: A table name wich relates to the test dataframe created for each pytest session
        :rtype: pyspark.sql.dataframe.DataFrame
        """

        # This dataset will be used to verify the DLT expectations in the bronze layer and the dropna in the silver layer
        random_data = []
        for _ in range(10):
            random_row = S.Row(
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

        random_df = spark.createDataFrame(random_data)

        #Replace empty string with None value for attribute cancellation_policy
        adding_none_to_random_df = random_df.withColumn(A.AttributesOriginal.cancellation_policy.name, \
            F.when(F.col(A.AttributesOriginal.cancellation_policy.name)==" " ,None) \
                .otherwise(F.col(A.AttributesOriginal.cancellation_policy.name)))

        
        # This row is used for verifying the aggregation UDF in the gold layer
        random_data_2 = []
        for _ in range(1):
            random_row_2 = S.Row(
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

            combined_random_df_str_nm = "default.test_dlt_combined_random_df"

            combined_random_df.write.format("delta").mode("overwrite").saveAsTable(combined_random_df_str_nm)

        return combined_random_df_str_nm