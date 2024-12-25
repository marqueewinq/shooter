# Shooter: full-page screenshot tool

Main use case of this applications is:

 - given a URL, take a full-page/partial screenshot;
 - detect all key elements on the page and label the resulting image with the found elements;
 - follow scripted user actions along the way.

REST API server runs all screenshot tasks in background.

## Docs

Each use case can be done through REST API or CLI.

REST API documentation is accessible by the `/docs` endpoint.

CLI documentation can be read here: `python -m shooter --help`.

### Architecture

The User sends HTTP request to API server. API server sends task(-s) to Task Broker. Several Workers are subscribed to
the Task Broker and pick up the tasks. Each Worker calls it's own `make_screenshot` function. The User can invoke 
`make_screenshot` function by themselves; the HTTP request schema matches the function signature:

<img src="./docs/diagrams/arch.png"/>

Each request contains one or more `TakeScreenshotConfig` objects ("configs"). Each config specifies one task, which will
be picked up by worker, and one invocation of the `make_screenshot` function. The config specifies the target URL and
several other parameters, including full page screenshot option, browser & device selection, whether to additionally 
capture HTML elements on the page, waiting options, proxy settings etc.

<img src="./docs/diagrams/request.png"/>

Each task will be put to the broker's queue separately (so different workers will pick up the tasks independently). At
the same time, all those tasks will form a _task group_. The task group is considered complete when all it's member 
tasks are complete; task group is considered failed if at least one task failed (other tasks will still be run and 
partial results will still be available).

<img src="./docs/diagrams/group_task.png"/>

The result of each task is two groups of artifacts. Given `--output_path`, the function creates them in the given 
folder. The actual results are: screenshot image, detected HTML elements (as JSON) and same screenshot
image labelled with those elements. The debug artifacts are: initial config (as JSON) and log file (as TXT).

Depending on the given parameters (`--capture_visible_elements` and `--capture_invisible_elements`), elements JSON and
the labelled image may be absent.

<img src="./docs/diagrams/output.png"/>

The user can queue status of his HTTP request (which corresponds to the status of the task group): number of total 
tasks, proceeded, failed and the overall status of the task group. When the task group is finished, user may request
the zip file; each task artifacts will be in the separate folder.

Here's the output zip structure:

```
<task group UUID>.zip
└── <URL>__<browser>__<fullpage?>__<config hash>
│   ├── config.json
│   ├── elements.json
│   ├── log.txt
│   ├── screenshot.labelled.png
│   └── screenshot.png
└── <URL>__<browser>__<fullpage?>__<config hash>
│   ...
```

The structure of `elements.json` is the following:

```
element = {
    "id": int,                     # Unique identifier
    "parent_id": int | null,       # ID of the parent element, or null if it's root element
    "bbox": [int, int, int, int],  # Bounding box as [x, y, width, height]
    "tag_name": string,            # HTML tag name (e.g., "div", "span")
    "label": string,               # Element's label or role description
    "position": string,            # Element's position (e.g., "absolute", "relative")
    "is_visible": boolean,         # Visibility status (true/false)
    "css_selector": string         # Unique CSS selector for the element
}

elements = [element, ...]  # List of elements
```

## Usage

Use case: based on the provided config, make a screenshot of the site.

Example (REST API):

```bash
curl -s -XPOST "http://$HOST:$PORT/take_screenshots/" \
     -H "Content-Type: application/json" \
     -d '{
           "sites": [
              "https://www.amazon.ae/"
           ],
           "default_config": {
             "device": "IPHONE_X",
             "browser": "chrome",
             "actions": [{"kind": "click_element", "element_query_selector": "#nav-hamburger-menu i"}]
           }
         }
```

Example (CLI):

```bash
PYTHONPATH=./ python shooter/screenshot.py https://www.amazon.ae/ ./output/ \
  --device=IPHONE_X \
  --browser=chrome \
  --actions='[{"kind": "click_element", "element_query_selector": "#nav-hamburger-menu i"}]'
```

In both of these examples the tool will make a screenshot of Amazon Store page using Chrome browser with IPhone X
parameters clicking the side menu before the capture.

The REST API endpoint will return the group task id, which then can be used to query the progress of the task group:

 - `/take_screenshots/{group_result_id}` will return the task group progress
 - `/take_screenshots/{group_result_id}/zip` will download the task group results as a single zip with the subfolder for
   each requested site.

#### Proxy usage examples

In REST API, `proxy` parameter can be passed in the following ways:

 - `None` (default) to not use the proxy
 - one instance of `ProxyConfig` objects
 - list of those objects (or `None`-s).

Script will try to connect with the first proxy on the list; if unsuccessful, it will try other proxies in the given
 order until success or the list is exhausted (this will raise `NoDriverRemainingError`).

Proxy config is the dict in the following form:

```json
{
  "host": "proxyserver.com",
  "port": 8989,
  "username": "proxyuser",
  "password": "imfirinmylaser",
  "protocol": "https"
}
```

`protocol` is optional (defaults to `https`), all other fields are required.

This `ProxyConfig` will be transformed to _connection string_ and passed to CLI as such.

In CLI, `--proxy` parameter can also be passed in these three ways. Instead of `ProxyConfig` object, CLI version uses
 _connection strings_. This is a handy way to pass all proxy parameters in one string.

Example of the connection string of the proxy config above:

```bash
python screenshot.py $URL $OUTPUT_DIR --proxy='https://proxyuser:imfirinmylaser@proxyserver.com:8989/'
```

The list can also be passed:

```bash
python screenshot.py $URL $OUTPUT_DIR \
  --proxy='["https://proxyuser:imfirinmylaser@proxyserver.com:8989/",\
            "https://proxyuser:imfirinmylaser@alternativeserver.com:8989/"]'
```

## Development

### Developer checklist

 - set up a virtualenv if needed: `virtualenv env --python=python3.12` and activate it
 - install pre-commit hooks: `pre-commit install`
   - if needed, install `pre-commit` first: `pip install pre-commit`

### Run the service with `docker-compose`

You can run a service in a docker container: `docker-compose --profile all up --build`

For concurrent execution, upscale the workers: `docker-compose --profile all up --build --scale worker=4`

Monitoring of the concurrent execution can be accessed via Flower: http://localhost:5555/

Description of the docker-compose profiles:

 - `all` profile runs the whole stack (excluding container with e2e tests) -- this is the go-to option for deployment.
 - `api` profile only deploys the REST API service (no tasks will be executed).
 - `e2e` profile runs the whole stack + the container with e2e tests (in `test.sh`).

#### `docker-compose` configuration

The results are saved to the directory specified by `OUTPUT_PATH` envvar; mount that to a volume to export.

Async task broker and result backend can be specified with `CELERY_BROKER_URL` and `CELERY_BACKEND_URL` envvars.

Container `e2e_tests` runs the `test.sh` script on start-up.

### Run the service locally

Alternatively, you can run the REST API from your machine:

 - install requirements: `pip install -e .`
 - run the service: `make run`

If you don't need the REST API server, you can run the screenshot script directly. Parameters are described here:
 `python -m shooter --help`.

### Testing

To run the unit tests locally:

 - install requirements: `pip install -e .[test]`
 - run pytest: `make unit_test`

Unit test coverage is saved in `./htmlcov` folder (open `./htmlcov/index.html` to view).

`docker-compose --profile e2e up --build --scale worker=4` runs end-to-end tests with 4 workers in parallel. See
`./test.sh` for details.
