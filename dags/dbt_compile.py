from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
import json

DBT_PROJECT_DIR = '/opt/airflow/dbt/dbt-training-bytecode-1'


dag = DAG(
    "dbt_compile",
    start_date=datetime(2020, 12, 23),
    default_args={"owner": "Bytecode", "email_on_failure": False},
    description="A sample Airflow DAG to invoke dbt runs using a BashOperator",
    schedule_interval=None,
    catchup=False,
)


dbt_compile = BashOperator(
        task_id = "dbt_compile",
        bash_command=f"dbt compile --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        dag=dag
    )

dbt_compile