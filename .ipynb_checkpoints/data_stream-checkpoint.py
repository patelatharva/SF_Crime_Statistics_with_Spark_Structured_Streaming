import logging
import json
from pyspark.sql import SparkSession
from pyspark.sql.types import *
import pyspark.sql.functions as psf
import pyspark.sql.functions as func

# TODO Create a schema for incoming resources
schema = StructType([
    StructField("crime_id", StringType(), False),
    StructField("original_crime_type_name", StringType(), True),
    StructField("report_date", DateType(), True),
    StructField("call_date", DateType(), True),
    StructField("offense_date", DateType(), True),
    StructField("call_time", StringType(), True),
    StructField("call_date_time", TimestampType(), True),
    StructField("disposition", StringType(), True),
    StructField("address", StringType(), True),
    StructField("city", StringType(), True),
    StructField("state", StringType(), True),
    StructField("agency_id", StringType(), True),
    StructField("address_type", StringType(), True),
    StructField("common_location", StringType(), True)
])

def run_spark_job(spark):

    # TODO Create Spark Configuration
    # Create Spark configurations with max offset of 200 per trigger
    # set up correct bootstrap server and port
#     https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "service-calls") \
        .option("maxOffsetsPerTrigger", 200) \
        .load()
        
    
    # Show schema for the incoming resources for checks
    df.printSchema()

    # TODO extract the correct column from the kafka input resources
    # Take only value and convert it to String
    kafka_df = df.selectExpr("CAST(value as STRING)")

    service_table = kafka_df\
        .select(psf.from_json(psf.col('value'), schema).alias("DF"))\
        .select("DF.*")

    # TODO select original_crime_type_name and disposition
    distinct_table = service_table.select("original_crime_type_name", "disposition")

    # count the number of original crime type
    agg_df = distinct_table.groupBy("original_crime_type_name").agg(func.count("*").alias("count"))

    # TODO Q1. Submit a screen shot of a batch ingestion of the aggregation
    # TODO write output stream
#     https://stackoverflow.com/questions/45092445/how-to-display-a-streaming-dataframe-as-show-fails-with-analysisexception
    query = agg_df \
                .writeStream \
                .outputMode("update") \
                .format("console") \
                .start()   


    # TODO attach a ProgressReporter
#     https://www.waitingforcode.com/apache-spark-structured-streaming/query-metrics-apache-spark-structured-streaming/read
    query.awaitTermination()

    # TODO get the right radio code json path
    radio_code_json_filepath = "radio_code.json"
    radio_code_df = spark.read.json(radio_code_json_filepath)

    # clean up your data so that the column names match on radio_code_df and agg_df
    # we will want to join on the disposition code

    # TODO rename disposition_code column to disposition
    radio_code_df = radio_code_df.withColumnRenamed("disposition_code", "disposition")

    # TODO join on disposition column
    join_query = agg_df.join(radio_code_df, radio_code_df.disposition == agg_df.disposition)


    join_query.awaitTermination()


if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    # TODO Create Spark in Standalone mode
    spark = SparkSession \
        .builder \
        .master("local[*]") \
        .appName("KafkaSparkStructuredStreaming") \
        .getOrCreate()

    logger.info("Spark started")

    run_spark_job(spark)

    spark.stop()
