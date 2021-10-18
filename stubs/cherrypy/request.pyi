from typing import Any, Dict, Union


class Request:
    prev: Any
    local: Any
    remote: Any
    scheme: str
    server_protocol: str
    base: str
    request_line: str
    method: str
    query_string: str
    query_string_encoding: str
    protocol: Any
    params: Any
    header_list: Any
    headers: Any
    cookie: Any
    rfile: Any
    process_request_body: bool
    methods_with_bodies: Any
    body: Any
    dispatch: Any
    script_name: str
    path_info: str
    login: Any
    app: Any
    handler: Any
    toolmaps: Any
    config: Any
    is_index: Any
    hooks: Any
    error_response: Any
    error_page: Any
    show_tracebacks: bool
    show_mismatched_params: bool
    throws: Any
    throw_errors: bool
    closed: bool
    stage: Any
    unique_id: Any
    namespaces: Any
    wants: str
    json: Dict[str, Union[str, int, float]]
