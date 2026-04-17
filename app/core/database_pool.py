"""
Database Connection Pool - Optimized Database Access
===============================================

Manages database connections with pooling, query optimization, and monitoring.
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, event
from sqlalchemy.pool import QueuePool
import threading

logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """Database query statistics."""
    query: str
    duration_ms: float
    rows_affected: int
    timestamp: float
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query[:100],  # First 100 chars
            "duration_ms": self.duration_ms,
            "rows_affected": self.rows_affected,
            "timestamp": self.timestamp,
            "success": self.success,
            "error": self.error
        }

@dataclass
class PoolStats:
    """Connection pool statistics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    overflow_connections: int
    checked_out_connections: int
    checked_in_connections: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class DatabaseConnectionPool:
    """Enhanced database connection pool with monitoring and optimization."""
    
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 30):
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        
        # Query monitoring
        self.query_stats: deque = deque(maxlen=10000)
        self.slow_queries: deque = deque(maxlen=1000)
        self.error_queries: deque = deque(maxlen=1000)
        
        # Performance thresholds
        self.slow_query_threshold = 500  # ms
        self.max_connection_age = 3600  # 1 hour
        
        # Pool monitoring
        self.pool_stats_history: deque = deque(maxlen=1000)
        self.connection_events: deque = deque(maxlen=5000)
        
        self._initialized = False
        
    async def initialize(self):
        """Initialize the database connection pool."""
        if self._initialized:
            return
        
        try:
            # Create async engine with optimized settings
            self.engine = create_async_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Validate connections
                pool_recycle=self.max_connection_age,
                echo=False,  # Disable SQL echo for production
                future=True,
                # Connection timeout settings
                connect_args={
                    "command_timeout": 30,
                    "server_settings": {
                        "application_name": "semptify_fastapi",
                        "jit": "off"  # Disable JIT for consistent performance
                    }
                }
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                future=True
            )
            
            # Register event listeners for monitoring
            self._register_event_listeners()
            
            self._initialized = True
            logger.info(f"Database connection pool initialized (size: {self.pool_size}, overflow: {self.max_overflow})")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def _register_event_listeners(self):
        """Register SQLAlchemy event listeners for monitoring."""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """Log new connections."""
            self.connection_events.append({
                "event": "connect",
                "timestamp": time.time(),
                "connection_id": id(connection_record)
            })
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkouts."""
            self.connection_events.append({
                "event": "checkout",
                "timestamp": time.time(),
                "connection_id": id(connection_record)
            })
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkins."""
            self.connection_events.append({
                "event": "checkin",
                "timestamp": time.time(),
                "connection_id": id(connection_record)
            })
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session from the pool."""
        if not self._initialized:
            await self.initialize()
        
        session = self.session_factory()
        start_time = time.time()
        
        try:
            yield session
            await session.commit()
            
            # Record successful session
            duration_ms = (time.time() - start_time) * 1000
            self.connection_events.append({
                "event": "session_success",
                "timestamp": time.time(),
                "duration_ms": duration_ms
            })
            
        except Exception as e:
            await session.rollback()
            
            # Record failed session
            duration_ms = (time.time() - start_time) * 1000
            self.connection_events.append({
                "event": "session_error",
                "timestamp": time.time(),
                "duration_ms": duration_ms,
                "error": str(e)
            })
            
            logger.error(f"Database session error: {e}")
            raise
            
        finally:
            await session.close()
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> Any:
        """Execute a database query with monitoring."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        success = False
        rows_affected = 0
        error = None
        
        try:
            async with self.get_session() as session:
                result = await session.execute(text(query), params or {})
                rows_affected = result.rowcount
                success = True
                
                # Record query stats
                duration_ms = (time.time() - start_time) * 1000
                stats = QueryStats(
                    query=query,
                    duration_ms=duration_ms,
                    rows_affected=rows_affected,
                    timestamp=start_time,
                    success=success
                )
                
                self.query_stats.append(stats)
                
                # Track slow queries
                if duration_ms > self.slow_query_threshold:
                    self.slow_queries.append(stats)
                
                # Log to performance monitor
                from app.core.performance_monitor import get_performance_monitor
                perf_monitor = get_performance_monitor()
                perf_monitor.record_database_query(query, duration_ms, rows_affected)
                
                return result
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error = str(e)
            
            # Record failed query
            stats = QueryStats(
                query=query,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
                timestamp=start_time,
                success=success,
                error=error
            )
            
            self.query_stats.append(stats)
            self.error_queries.append(stats)
            
            logger.error(f"Database query failed: {query[:100]}... - {error}")
            raise
    
    async def execute_batch(self, queries: List[tuple]) -> List[Any]:
        """Execute multiple queries in a batch."""
        if not self._initialized:
            await self.initialize()
        
        results = []
        start_time = time.time()
        
        try:
            async with self.get_session() as session:
                for query, params in queries:
                    result = await session.execute(text(query), params or {})
                    results.append(result)
                
                # Record batch stats
                duration_ms = (time.time() - start_time) * 1000
                self.query_stats.append(QueryStats(
                    query=f"BATCH: {len(queries)} queries",
                    duration_ms=duration_ms,
                    rows_affected=sum(r.rowcount for r in results),
                    timestamp=start_time,
                    success=True
                ))
                
                return results
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Record failed batch
            self.query_stats.append(QueryStats(
                query=f"BATCH: {len(queries)} queries",
                duration_ms=duration_ms,
                rows_affected=0,
                timestamp=start_time,
                success=False,
                error=str(e)
            ))
            
            logger.error(f"Database batch query failed: {e}")
            raise
    
    def get_pool_stats(self) -> PoolStats:
        """Get current connection pool statistics."""
        if not self.engine:
            return PoolStats(0, 0, 0, 0, 0, 0)
        
        pool = self.engine.sync_engine.pool
        
        stats = PoolStats(
            total_connections=pool.size(),
            active_connections=pool.checkedout(),
            idle_connections=pool.checkedin(),
            overflow_connections=pool.overflow(),
            checked_out_connections=pool.checkedout(),
            checked_in_connections=pool.checkedin()
        )
        
        self.pool_stats_history.append(stats)
        return stats
    
    def get_query_stats(self, hours: int = 1) -> Dict[str, Any]:
        """Get query performance statistics."""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_queries = [
            stat for stat in self.query_stats
            if stat.timestamp >= cutoff_time
        ]
        
        if not recent_queries:
            return {
                "total_queries": 0,
                "average_duration_ms": 0,
                "slow_queries": 0,
                "error_rate_percent": 0,
                "rows_affected_total": 0
            }
        
        durations = [q.duration_ms for q in recent_queries]
        slow_count = len([q for q in recent_queries if q.duration_ms > self.slow_query_threshold])
        error_count = len([q for q in recent_queries if not q.success])
        
        return {
            "total_queries": len(recent_queries),
            "average_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "p95_duration_ms": self._percentile(durations, 95),
            "slow_queries": slow_count,
            "slow_query_rate_percent": (slow_count / len(recent_queries)) * 100,
            "error_rate_percent": (error_count / len(recent_queries)) * 100,
            "rows_affected_total": sum(q.rows_affected for q in recent_queries)
        }
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get slow queries."""
        return [stat.to_dict() for stat in list(self.slow_queries)[-limit:]]
    
    def get_error_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get failed queries."""
        return [stat.to_dict() for stat in list(self.error_queries)[-limit:]]
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def optimize_database(self):
        """Run database optimization tasks."""
        if not self._initialized:
            await self.initialize()
        
        optimization_queries = [
            # Update statistics
            ("ANALYZE", {}),
            # Clean up dead rows
            ("VACUUM ANALYZE", {}),
            # Reindex if needed
            ("REINDEX DATABASE", {}),
        ]
        
        try:
            await self.execute_batch(optimization_queries)
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Test basic connectivity
            await self.execute_query("SELECT 1")
            
            # Get pool stats
            pool_stats = self.get_pool_stats()
            
            # Get query stats
            query_stats = self.get_query_stats(hours=1)
            
            health_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": health_time,
                "pool_stats": pool_stats.to_dict(),
                "query_stats": query_stats,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "timestamp": time.time()
            }
    
    async def close(self):
        """Close the database connection pool."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connection pool closed")

# Global database pool instance
_database_pool: Optional[DatabaseConnectionPool] = None

async def get_database_pool() -> DatabaseConnectionPool:
    """Get the global database connection pool."""
    global _database_pool
    
    if _database_pool is None:
        from app.core.config import get_settings
        settings = get_settings()
        
        _database_pool = DatabaseConnectionPool(
            database_url=settings.database_url,
            pool_size=settings.db_pool_size if hasattr(settings, 'db_pool_size') else 20,
            max_overflow=settings.db_max_overflow if hasattr(settings, 'db_max_overflow') else 30
        )
        
        await _database_pool.initialize()
    
    return _database_pool

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    pool = await get_database_pool()
    async with pool.get_session() as session:
        yield session

# Helper functions
async def execute_query(query: str, params: Dict[str, Any] = None) -> Any:
    """Execute a database query."""
    pool = await get_database_pool()
    return await pool.execute_query(query, params)

async def get_database_health() -> Dict[str, Any]:
    """Get database health status."""
    pool = await get_database_pool()
    return await pool.health_check()

async def optimize_database():
    """Optimize the database."""
    pool = await get_database_pool()
    await pool.optimize_database()

# Query optimization helpers
def build_optimized_query(base_query: str, filters: Dict[str, Any] = None, 
                         order_by: str = None, limit: int = None, 
                         offset: int = None) -> tuple:
    """Build an optimized SQL query."""
    query_parts = [base_query]
    params = {}
    
    # Add WHERE clauses
    if filters:
        where_clauses = []
        for i, (key, value) in enumerate(filters.items()):
            param_name = f"param_{i}"
            where_clauses.append(f"{key} = :{param_name}")
            params[param_name] = value
        
        if where_clauses:
            query_parts.append(f"WHERE {' AND '.join(where_clauses)}")
    
    # Add ORDER BY
    if order_by:
        query_parts.append(f"ORDER BY {order_by}")
    
    # Add LIMIT and OFFSET
    if limit:
        query_parts.append(f"LIMIT {limit}")
        if offset:
            query_parts.append(f"OFFSET {offset}")
    
    final_query = " ".join(query_parts)
    return final_query, params

# Performance monitoring decorator
def monitor_query_performance(func):
    """Decorator to monitor query performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log performance
            from app.core.performance_monitor import get_performance_monitor
            perf_monitor = get_performance_monitor()
            perf_monitor._store_metric(
                f"query.{func.__name__}", 
                duration_ms, 
                "ms"
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error performance
            from app.core.performance_monitor import get_performance_monitor
            perf_monitor = get_performance_monitor()
            perf_monitor._store_metric(
                f"query.{func.__name__}.errors", 
                1, 
                "count"
            )
            
            raise
    
    return wrapper
