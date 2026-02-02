import axios from 'axios';

// Simple Circuit Breaker Implementation for Frontend
class CircuitBreakerRegistry {
  constructor() {
    this.breakers = new Map();
  }

  get(name) {
    if (!this.breakers.has(name)) {
      this.breakers.set(name, {
        state: 'CLOSED',
        failures: 0,
        nextAttempt: 0,
        config: { threshold: 3, timeout: 5000 },
      });
    }
    return this.breakers.get(name);
  }

  async guard(name, action) {
    const breaker = this.get(name);
    const now = Date.now();

    if (breaker.state === 'OPEN') {
      if (now > breaker.nextAttempt) {
        breaker.state = 'HALF_OPEN';
      } else {
        throw new Error(`CircuitBreaker '${name}' is OPEN`);
      }
    }

    try {
      const result = await action();
      if (breaker.state === 'HALF_OPEN') {
        breaker.state = 'CLOSED';
        breaker.failures = 0;
      }
      return result;
    } catch (error) {
      this.recordFailure(breaker, name);
      throw error;
    }
  }

  recordFailure(breaker, name) {
    breaker.failures++;
    if (breaker.failures >= breaker.config.threshold) {
      breaker.state = 'OPEN';
      breaker.nextAttempt = Date.now() + breaker.config.timeout;
      console.warn(`Circuit '${name}' Opened due to ${breaker.failures} failures.`);

      // Notify UI
      window.dispatchEvent(
        new CustomEvent('api-error', {
          detail: { type: 'CIRCUIT_BREAKER_OPEN', message: `Proteção ativa para ${name}.` },
        })
      );
    }
  }
}

const registry = new CircuitBreakerRegistry();

export const ResilienceService = {
  // Tracing Wrapper
  async executeWithTracing(operationName, action) {
    const traceId = crypto.randomUUID();
    console.log(`[Trace:${traceId}] Starting ${operationName}`);
    const start = performance.now();

    try {
      // Pass context if needed, here just logging
      const result = await action({ traceId });
      const duration = (performance.now() - start).toFixed(2);
      console.log(`[Trace:${traceId}] Success ${operationName} (${duration}ms)`);
      return result;
    } catch (error) {
      const duration = (performance.now() - start).toFixed(2);
      console.error(`[Trace:${traceId}] Failed ${operationName} (${duration}ms)`, error);
      throw error;
    }
  },

  // Facade for Circuit Breaker
  async guard(componentName, action) {
    return registry.guard(componentName, action);
  },
};
