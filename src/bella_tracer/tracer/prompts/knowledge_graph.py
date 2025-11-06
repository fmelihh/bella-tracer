DETECTIVE_PROMPT_TEMPLATE = """
You are a log analysis expert. Your task is to analyze a raw log message, extract 
structured entities, and summarize errors.

Rules:
1.  Extract Entities: Identify key business entities (e.g., 'order_id').
2.  Summarize Stack Trace: If the message is a stack trace (e.g., 'httpx.ConnectError'), 
    summarize the root cause and the file/line where it occurred.
3.  Extract Relationships: Identify relationships between entities.

Return ONLY a valid JSON object with your findings.

Log Message:
"{message}"

JSON Output:
"""

ARCHITECT_PROMPT_TEMPLATE = """
You are a senior data architect. Your task is to convert two JSON inputs
(the original log and its analysis) into ONE single Neo4j Cypher query,
based on the provided schema. You must output exactly one continuous Cypher
statement that can be executed as-is, with only one semicolon at the very end.
Do not include comments, explanations, markdown fences, or parameters. Embed
all literal values directly in the Cypher you produce.

Graph Schema:
- :Service(name:String), :Trace(id:String), :Order(id:String)
- :Log(timestamp:String, level:String, message:String, funcName:String)
- :Error(type:String, message:String)
- :Metric(type:String, value:Float)
- Relationships: [:PRODUCES_LOG], [:PART_OF_TRACE], [:HAS_EVENT], [:TRIGGERED_BY],
  [:PRODUCED_ERROR], [:REPORTS_METRIC], [:FAILS_TO_CALL]

Strict rules (follow exactly):
0) Single statement: Build everything for this one log entry in a single Cypher query. Use WITH to pass variables.
   End the entire statement with exactly one semicolon.
1) Use MERGE for core entities (:Service, :Trace, :Order). Use CREATE for event-like nodes (:Log, :Error, :Metric).
2) Always create and wire the core :Log node first, in this exact order:
   MERGE (t:Trace {{id: '<TRACE_ID>'}})
   MERGE (s:Service {{name: '<SERVICE_NAME>'}})
   CREATE (l:Log {{timestamp: '<TS>', level: '<LEVEL>', message: '<MESSAGE>', funcName: '<FUNC>'}})
   CREATE (s)-[:PRODUCES_LOG]->(l)
   CREATE (l)-[:PART_OF_TRACE]->(t)
   WITH l
   Where the placeholders come from:
     - <TRACE_ID>      = log_input_json.trace_id
     - <SERVICE_NAME>  = log_input_json.service
     - <TS>            = log_input_json.timestamp
     - <LEVEL>         = log_input_json.level
     - <MESSAGE>       = log_input_json.message   (escape internal single quotes by doubling them)
     - <FUNC>          = log_input_json.funcName
3) NEVER use keys() on a JSON literal, and NEVER create a Cypher map with quoted keys (e.g., {{\"cpu_percent\": 12.3}} is invalid).
   If metrics exist in log_input_json.metrics, construct a list-of-pairs and UNWIND it. Example pattern:
     WITH l
     UNWIND [
       {{type: 'cpu_percent', value: 23.18}},
       {{type: 'memory_percent', value: 46.69}}
     ] AS m
     CREATE (mx:Metric {{type: m.type, value: m.value}})
     CREATE (l)-[:REPORTS_METRIC]->(mx)
   Generate the list from the actual keys/values present in log_input_json.metrics.
   If there are no metrics, skip this block entirely.
4) Duration metric:
   If a duration (milliseconds) is available, prefer analysis_result_json.duration_ms.
   Otherwise, if log_input_json.message contains a pattern like \"finished in N ms\" or \"N.ms\", extract N as a float.
   When present, add:
     WITH l
     CREATE (m_dur:Metric {{type: 'duration_ms', value: <DURATION_MS_FLOAT>}})
     CREATE (l)-[:REPORTS_METRIC]->(m_dur)
5) Enrichment from analysis_result_json:
   - If entities.order_id exists:
       WITH l
       MERGE (o:Order {{id: '<ORDER_ID>'}})
       CREATE (l)-[:HAS_EVENT]->(o)
   - If there is a failed downstream service (e.g., analysis_result_json.failed_service_name):
       WITH l
       MERGE (s_target:Service {{name: '<FAILED_SERVICE_NAME>'}})
       CREATE (l)-[:FAILS_TO_CALL]->(s_target)
6) Errors:
   If analysis_result_json.error_summary exists (with fields like type and message), create and link:
     WITH l
     CREATE (err:Error {{type: '<ERROR_TYPE>', message: '<ERROR_MESSAGE>'}})
     CREATE (l)-[:PRODUCED_ERROR]->(err)
   Escape any single quotes in strings by doubling them.
7) String vs number:
   - Strings must be single-quoted in Cypher.
   - Numeric values (including metric values and duration) must be unquoted.
8) Do not use parameters (no $param), apoc procedures, or CALLs. Only use MERGE/CREATE/UNWIND/WITH/RETURN as needed.
9) Output only the Cypher query and nothing else. End with a single semicolon.

Input 1: Original Log JSON:
{log_input_json}

Input 2: Analysis Result JSON:
{analysis_result_json}

Cypher Query:
"""


__all__ = ["DETECTIVE_PROMPT_TEMPLATE", "ARCHITECT_PROMPT_TEMPLATE"]
