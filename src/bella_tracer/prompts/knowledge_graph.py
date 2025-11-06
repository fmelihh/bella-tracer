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
(the original log and its analysis) into a series of Neo4j Cypher queries 
based on the provided schema.

**Graph Schema:**
- :Service(name:String), :Trace(id:String), :Order(id:String)
- :Log(timestamp:String, level:String, message:String, funcName:String)
- :Error(type:String, message:String)
- :Metric(type:String, value:Float)
- (Relationships): 
  [:PRODUCES_LOG], [:PART_OF_TRACE], [:HAS_EVENT], [:TRIGGERED_BY], 
  [:PRODUCED_ERROR], [:REPORTS_METRIC], [:FAILS_TO_CALL]

**Rules:**
1.  Use `MERGE` for core nodes (:Service, :Trace, :Order), `CREATE` for event nodes (:Log, :Error, :Metric).
2.  **Create the core `:Log` node for this entry:**
    a.  `MERGE (t:Trace {id: original_log_json.trace_id})`
    b.  `MERGE (s:Service {name: original_log_json.service})`
    c.  `CREATE (l:Log { 
            timestamp: original_log_json.timestamp, 
            level: original_log_json.level, 
            message: original_log_json.message, 
            funcName: original_log_json.funcName 
         })`
    d.  `CREATE (s)-[:PRODUCES_LOG]->(l)`
    e.  `CREATE (l)-[:PART_OF_TRACE]->(t)`
3.  **Create `:Metric` nodes (and link them to the new :Log node):**
    a.  If `original_log_json.metrics` (like cpu_percent, memory_percent) exist:
        `WITH l
         UNWIND keys(original_log_json.metrics) AS metric_type
         MERGE (m:Metric {type: metric_type, value: original_log_json.metrics[metric_type]})
         CREATE (l)-[:REPORTS_METRIC]->(m)`
    b.  If `original_log_json.message` contains a duration (e.g., "finished in 123.45ms"):
        `WITH l
         MERGE (m_dur:Metric {type: 'duration_ms', value: 123.45})
         CREATE (l)-[:REPORTS_METRIC]->(m_dur)`
4.  **Use `analysis_result_json` for deeper relationships (link to :Log node):**
    a.  If `analysis_result_json.entities.order_id` exists:
        `WITH l
         MERGE (o:Order {id: analysis_result_json.entities.order_id})
         CREATE (l)-[:HAS_EVENT]->(o)`
    b.  If `analysis_result_json` mentions a service call failure (e.g., 'FAILS_TO_CALL: fraud-service'):
        `WITH l
         MERGE (s_target:Service {name: 'fraud-service'})
         CREATE (l)-[:FAILS_TO_CALL]->(s_target)`
5.  **If `analysis_result_json` contains an `error_summary` (link to :Log node):**
    `WITH l
     CREATE (err:Error { 
        type: analysis_result_json.error_summary.type, 
        message: analysis_result_json.error_summary.message 
     })
     CREATE (l)-[:PRODUCED_ERROR]->(err)`
6.  Output ONLY the Cypher queries, separated by semicolons.

**Input 1: Original Log JSON:**
{original_log_json}

**Input 2: Analysis Result JSON:**
{analysis_result_json}

**Cypher Query:**
"""


__all__ = ["DETECTIVE_PROMPT_TEMPLATE", "ARCHITECT_PROMPT_TEMPLATE"]
