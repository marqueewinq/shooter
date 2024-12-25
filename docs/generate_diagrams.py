import fire
from graphviz import Digraph


def draw_diagram_architecture(output_path: str):
    # Create a directed graph
    diagram = Digraph("TaskFlow", format="png")
    diagram.attr(rankdir="TB", nodesep="0.5", ranksep="0.8")

    # Nodes
    diagram.node("User", "Actor: User", shape="oval", style="filled", color="lightblue")
    diagram.node("API", "API Server", shape="box", style="filled", color="lightgray")
    diagram.node(
        "Broker",
        "Task Broker",
        shape="parallelogram",
        style="filled",
        color="lightyellow",
    )
    diagram.node(
        "Worker_1", "Worker 1", shape="ellipse", style="filled", color="lightgreen"
    )
    diagram.node(
        "Worker_2", "Worker 2", shape="ellipse", style="filled", color="lightgreen"
    )
    diagram.node(
        "Worker_3", "Worker 3", shape="ellipse", style="filled", color="lightgreen"
    )
    diagram.node(
        "Screenshot_1",
        "make_screenshot",
        shape="box",
        style="filled",
        color="lightgoldenrod1",
    )
    diagram.node(
        "Screenshot_2",
        "make_screenshot",
        shape="box",
        style="filled",
        color="lightgoldenrod1",
    )
    diagram.node(
        "Screenshot_3",
        "make_screenshot",
        shape="box",
        style="filled",
        color="lightgoldenrod1",
    )
    diagram.node(
        "Screenshot",
        "make_screenshot",
        shape="box",
        style="filled",
        color="lightgoldenrod1",
    )

    # Connections
    # Path 1: User -> API Server -> Task Broker -> Worker -> make_screenshot
    diagram.edge("User", "API", label="HTTP request", arrowhead="vee", arrowsize="1.0")
    diagram.edge("API", "Broker", label="Send Task", arrowhead="vee", arrowsize="1.0")
    diagram.edge("Broker", "Worker_1", label="", arrowhead="vee", arrowsize="1.0")
    diagram.edge(
        "Broker", "Worker_2", label="Distribute Task", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge("Broker", "Worker_3", label="", arrowhead="vee", arrowsize="1.0")
    diagram.edge(
        "Worker_1", "Screenshot_1", label="Invoke", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "Worker_2", "Screenshot_2", label="Invoke", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "Worker_3", "Screenshot_3", label="Invoke", arrowhead="vee", arrowsize="1.0"
    )

    # Path 2: User -> make_screenshot (direct)
    diagram.edge(
        "User",
        "Screenshot",
        label="Direct Invocation",
        arrowhead="vee",
        arrowsize="1.0",
    )

    # Render the diagram
    diagram.render(output_path, format="png", cleanup=True)


def draw_request_diagram(output_path: str):
    # Create a directed graph
    diagram = Digraph("RequestFlow", format="png")
    diagram.attr(rankdir="TB", nodesep="0.5", ranksep="0.8")

    # Nodes
    diagram.node("User", "Actor: User", shape="oval", style="filled", color="lightblue")
    diagram.node(
        "HTTPRequest", "HTTP Request", shape="box", style="filled", color="lightgray"
    )
    diagram.node(
        "Config_1",
        "Config 1",
        shape="parallelogram",
        style="filled",
        color="lightyellow",
    )
    diagram.node(
        "Config_2",
        "Config 2",
        shape="parallelogram",
        style="filled",
        color="lightyellow",
    )
    diagram.node(
        "Config_3",
        "Config 3",
        shape="parallelogram",
        style="filled",
        color="lightyellow",
    )
    diagram.node(
        "Screenshot_1", "Task 1", shape="box", style="filled", color="lightgoldenrod1"
    )
    diagram.node(
        "Screenshot_2", "Task 2", shape="box", style="filled", color="lightgoldenrod1"
    )
    diagram.node(
        "Screenshot_3", "Task 3", shape="box", style="filled", color="lightgoldenrod1"
    )

    # Connections
    # Path: User -> HTTP Request -> Configs -> make_screenshot
    diagram.edge(
        "User", "HTTPRequest", label="Provides", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "HTTPRequest", "Config_1", label="Includes", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "HTTPRequest", "Config_2", label="Includes", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "HTTPRequest", "Config_3", label="Includes", arrowhead="vee", arrowsize="1.0"
    )
    diagram.edge(
        "Config_1",
        "Screenshot_1",
        label="Processed by",
        arrowhead="vee",
        arrowsize="1.0",
    )
    diagram.edge(
        "Config_2",
        "Screenshot_2",
        label="Processed by",
        arrowhead="vee",
        arrowsize="1.0",
    )
    diagram.edge(
        "Config_3",
        "Screenshot_3",
        label="Processed by",
        arrowhead="vee",
        arrowsize="1.0",
    )

    # Add subgraph to group make_screenshot nodes

    with diagram.subgraph(name="cluster_task_group") as cluster:
        cluster.attr(label="Group Task", style="filled", color="lightgoldenrod2")
        cluster.node("Screenshot_1")
        cluster.node("Screenshot_2")
        cluster.node("Screenshot_3")

    # Render the diagram
    diagram.render(output_path, format="png", cleanup=True)


def draw_horizontal_combined_task_group_diagram(output_path: str):
    # Create a single combined diagram
    diagram = Digraph("HorizontalTaskGroupRules", format="png")

    # Subgraph for failed task group
    with diagram.subgraph(name="cluster_failed") as failed_group:
        failed_group.attr(
            label="Task Group: Failed",
            style="filled",
            color="lightgoldenrod2",
            fontcolor="black",
        )
        failed_group.node(
            "Failed_Task_1", "Task 1", shape="box", style="filled", color="lightgreen"
        )
        failed_group.node(
            "Failed_Task_2", "Task 2", shape="box", style="filled", color="lightgreen"
        )
        failed_group.node(
            "Failed_Task_3", "Task 3", shape="box", style="filled", color="lightcoral"
        )
        failed_group.edges(
            [
                ("Failed_Task_1", "Failed_Group"),
                ("Failed_Task_2", "Failed_Group"),
                ("Failed_Task_3", "Failed_Group"),
            ]
        )
        failed_group.node(
            "Failed_Group",
            "Task Group",
            shape="ellipse",
            style="filled",
            color="lightcoral",
        )

    # Subgraph for successful task group
    with diagram.subgraph(name="cluster_success") as success_group:
        success_group.attr(
            label="Task Group: Success",
            style="filled",
            color="lightgoldenrod2",
            fontcolor="black",
        )
        success_group.node(
            "Success_Task_1", "Task 1", shape="box", style="filled", color="lightgreen"
        )
        success_group.node(
            "Success_Task_2", "Task 2", shape="box", style="filled", color="lightgreen"
        )
        success_group.node(
            "Success_Task_3", "Task 3", shape="box", style="filled", color="lightgreen"
        )
        success_group.edges(
            [
                ("Success_Task_1", "Success_Group"),
                ("Success_Task_2", "Success_Group"),
                ("Success_Task_3", "Success_Group"),
            ]
        )
        success_group.node(
            "Success_Group",
            "Task Group",
            shape="ellipse",
            style="filled",
            color="lightgreen",
        )

    # Render the combined diagram
    diagram.render(output_path, format="png", cleanup=True)


def draw_task_artifacts_diagram(output_path: str):
    # Create the diagram
    diagram = Digraph("TaskArtifacts", format="png")
    diagram.attr(rankdir="TB", nodesep="1.0", ranksep="1.5")

    # Main task node
    diagram.node(
        "Task",
        "Completed task",
        shape="ellipse",
        style="filled",
        color="lightgoldenrod1",
    )

    # Result artifacts
    diagram.node(
        "Screenshot", "Screenshot (PNG)", shape="box", style="filled", color="green"
    )
    diagram.node(
        "Labeled_Screenshot",
        "Labeled Screenshot (PNG)",
        shape="box",
        style="filled",
        color="lightgreen",
    )
    diagram.node(
        "HTML_Elements",
        "Detected HTML Elements (JSON)",
        shape="box",
        style="filled",
        color="lightgreen",
    )

    # Debug artifacts
    diagram.node(
        "Config_JSON",
        "Initial Config (JSON)",
        shape="box",
        style="filled",
        color="lightyellow",
    )
    diagram.node(
        "Log_File", "Log File (TXT)", shape="box", style="filled", color="lightyellow"
    )

    # Edges from Task to artifacts
    diagram.edge("Task", "Screenshot", arrowhead="vee", arrowsize="1.0")
    diagram.edge("Task", "HTML_Elements", arrowhead="vee", arrowsize="1.0")
    diagram.edge("Task", "Labeled_Screenshot", arrowhead="vee", arrowsize="1.0")
    diagram.edge("Task", "Config_JSON", arrowhead="vee", arrowsize="1.0")
    diagram.edge("Task", "Log_File", arrowhead="vee", arrowsize="1.0")

    # Subgraphs for grouping
    with diagram.subgraph(name="cluster_results") as results_group:
        results_group.attr(label="Result Artifacts", style="dashed", color="black")
        results_group.node("Screenshot")
        results_group.node("HTML_Elements")
        results_group.node("Labeled_Screenshot")

    with diagram.subgraph(name="cluster_debug") as debug_group:
        debug_group.attr(label="Debug Artifacts", style="dashed", color="black")
        debug_group.node("Config_JSON")
        debug_group.node("Log_File")

    # Render the diagram
    diagram.render(output_path, format="png", cleanup=True)


def draw_all():
    draw_diagram_architecture("docs/diagrams/arch")
    draw_request_diagram("docs/diagrams/request")
    draw_horizontal_combined_task_group_diagram("docs/diagrams/group_task")
    draw_task_artifacts_diagram("docs/diagrams/output")


if __name__ == "__main__":
    fire.Fire(draw_all)
