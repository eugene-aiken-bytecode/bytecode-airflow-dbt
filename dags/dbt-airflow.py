from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.utils.task_group import TaskGroup
import json

# We're hardcoding this value here for the purpose of the demo, but in a production environment this
# would probably come from a config file and/or environment variables!
DBT_PROJECT_DIR = '/opt/airflow/dbt/dbt-training-bytecode-1'

def load_manifest():
    local_filepath = f"{DBT_PROJECT_DIR}/target/manifest.json"
    with open(local_filepath) as f:
        data = json.load(f)
    return data

def make_dbt_task(node, dbt_verb):
    """Returns an Airflow operator either run and test an individual model"""
    GLOBAL_CLI_FLAGS = "--no-write-json"
    model = node.split(".")[-1]
    if dbt_verb == "run":
        dbt_task = BashOperator(
            task_id=node,
            bash_command=f"""
            dbt {GLOBAL_CLI_FLAGS} {dbt_verb} --target dev --models {model} \
            --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}
            """,
            dag=dag,
        )
    elif dbt_verb == "test":
        node_test = node.replace("model", "test")
        dbt_task = BashOperator(
            task_id=node_test,
            bash_command=f"""
            dbt {GLOBAL_CLI_FLAGS} {dbt_verb} --target dev --models {model} \
            --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}
            """,
            dag=dag,
        )
    return dbt_task

dag = DAG(
    "dbt_training_bytecode",
    start_date=datetime(2020, 12, 23),
    default_args={"owner": "Bytecode", "email_on_failure": False},
    description="A sample Airflow DAG to invoke dbt runs using a BashOperator",
    schedule_interval=None,
    catchup=False,
)


    # This task loads the CSV files from dbt/data into the local postgres database for the purpose of this demo.
    # In practice, we'd usually expect the data to have already been loaded to the database.

dbt_deps = BashOperator(
        task_id = "dbt_deps",
        bash_command=f"dbt deps --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        dag=dag
    )

dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"dbt seed --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        dag=dag
    )

data = load_manifest()
dbt_tasks = {}

for node in data["nodes"].keys():
    if node.split(".")[0] == "model":
        node_test = node.replace("model", "test")
        dbt_tasks[node] = make_dbt_task(node, "run")
        dbt_tasks[node_test] = make_dbt_task(node, "test")

for node in data["nodes"].keys():
    if node.split(".")[0] == "model":
        # Set dependency to run tests on a model after model runs finishes
        node_test = node.replace("model", "test")
        dbt_tasks[node] >> dbt_tasks[node_test]
        # Set all model -> model dependencies
        for upstream_node in data["nodes"][node]["depends_on"]["nodes"]:
            upstream_node_type = upstream_node.split(".")[0]
            if upstream_node_type == "model":
                dbt_deps >> dbt_seed >> dbt_tasks[upstream_node] >> dbt_tasks[node]
