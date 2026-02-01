
import unittest
import threading
import structlog
from backend.core.logger import set_trace_id, get_trace_id, configure_logging, get_logger

# Configure structlog to capture output for testing (using a list)
captured_logs = []

def capture_processor(logger, method_name, event_dict):
    captured_logs.append(event_dict)
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        capture_processor, 
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = get_logger(__name__)

class TestTracingPropagation(unittest.TestCase):
    def setUp(self):
        captured_logs.clear()
        
    def test_trace_id_propagation_to_thread(self):
        # 1. Simulate Middleware (Main Thread)
        main_trace_id = "test-trace-123"
        set_trace_id(main_trace_id)
        structlog.contextvars.bind_contextvars(trace_id=main_trace_id)
        
        logger.info("request_received")
        
        # Verify middleware log has trace_id
        self.assertTrue(any(l.get('trace_id') == main_trace_id for l in captured_logs))
        
        # 2. Simulate Background Job (New Thread)
        def job_worker(restored_trace_id):
            # Restore context
            set_trace_id(restored_trace_id)
            structlog.contextvars.bind_contextvars(trace_id=restored_trace_id)
            
            # Log from "Service"
            logger.info("job_processing")
            
            # Verify context inside thread
            self.assertEqual(get_trace_id(), main_trace_id)
            
        t = threading.Thread(target=job_worker, args=(main_trace_id,))
        t.start()
        t.join()
        
        # 3. Verify Thread Log has trace_id
        job_logs = [l for l in captured_logs if l.get('event') == 'job_processing']
        self.assertEqual(len(job_logs), 1)
        self.assertEqual(job_logs[0].get('trace_id'), main_trace_id)
        
        print("Tracing Propagation Verified: Main -> Thread -> Service Log")

if __name__ == "__main__":
    unittest.main()
