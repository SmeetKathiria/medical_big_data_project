from __future__ import annotations

import os

from pyspark.sql import SparkSession


def get_spark(app_name: str = "medintel-local") -> SparkSession:
    os.environ.setdefault("PYSPARK_PYTHON", os.environ.get("PYTHON", ".venv/bin/python"))
    return (
        SparkSession.builder.appName(app_name)
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "4"))
        .config("spark.ui.enabled", os.getenv("SPARK_UI_ENABLED", "false"))
        .getOrCreate()
    )
