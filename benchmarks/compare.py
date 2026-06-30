"""
Benchmark ReduxToken — compara economia de tokens por tipo de conteúdo.
Uso: python benchmarks/compare.py
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from redux_token import ReduxToken

rt = ReduxToken()

LOG = """
[DEBUG] 2024-01-15 10:00:01 - Loading configuration from /etc/app/config.yaml
[DEBUG] 2024-01-15 10:00:01 - Connecting to database at db.internal:5432
[TRACE] 2024-01-15 10:00:01 - Query: SELECT * FROM users WHERE active = true
[DEBUG] 2024-01-15 10:00:02 - Cache miss for key: user_profile_123
[INFO]  2024-01-15 10:00:02 - Server initialized successfully
[DEBUG] 2024-01-15 10:00:02 - Health check passed
[DEBUG] 2024-01-15 10:00:02 - Health check passed
[DEBUG] 2024-01-15 10:00:03 - Health check passed
[INFO]  2024-01-15 10:00:03 - Ready to accept connections on port 8080
======================================================
[DEBUG] 2024-01-15 10:00:04 - Request: GET /api/users/123
[TRACE] 2024-01-15 10:00:04 - JWT token validated for user_id=42
[DEBUG] 2024-01-15 10:00:04 - DB query returned 1 row in 12ms
[INFO]  2024-01-15 10:00:04 - Response 200 OK sent in 14ms
======================================================
""" * 5

JSON_PAYLOAD = json.dumps({
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "_id": "507f1f77bcf86cd799439011",
    "uuid": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "deleted_at": None,
    "created_by": "admin",
    "updated_by": "system",
    "timestamp": 1705315800,
    "timestamps": {"start": 1705315800, "end": 1705315860},
    "metadata": {"source": "api", "version": 3, "env": "prod"},
    "deprecated": False,
    "version": "2.1.0",
    "name": "Maria Silva",
    "email": "maria@exemplo.com",
    "role": "admin",
    "department": "Engineering",
    "active": True,
    "permissions": ["read", "write", "deploy"],
}, indent=2) * 3

CODE = """
/**
 * UserService - handles all user-related business logic.
 * This service is responsible for CRUD operations on users.
 * @author Engineering Team
 * @version 2.1.0
 */
class UserService {
    // Maximum number of retries for failed operations
    private static final int MAX_RETRIES = 3;

    // Default timeout in milliseconds
    private static final int TIMEOUT_MS = 5000;

    /**
     * Retrieves a user by their unique identifier.
     * Returns null if user is not found.
     * @param userId the unique user ID
     * @return User object or null
     */
    public User getUserById(String userId) {
        // Validate input before querying
        if (userId == null || userId.isEmpty()) {
            return null; // Return null for invalid input
        }
        return repository.findById(userId); // Query database
    }
}
""" * 4

REPETITIVE = (
    "status: healthy\nversion: 2.1.0\nregion: us-east-1\n"
    "status: healthy\nversion: 2.1.0\nregion: us-east-1\n"
    "status: healthy\nversion: 2.1.0\nregion: us-east-1\n"
) * 10

scenarios = [
    ("Log (app noise)",      LOG),
    ("JSON (metadata-heavy)", JSON_PAYLOAD),
    ("Code (comments)",      CODE),
    ("Repetitive text",      REPETITIVE),
]

header = f"{'Cenario':<26} {'Tokens':>8} {'->':>2} {'Comprimido':>10} {'Economia':>9} {'Tempo':>8}"
print(header)
print("-" * len(header))

total_orig = total_comp = 0
for name, text in scenarios:
    _, stats = rt.compress(text)
    total_orig += stats.original_tokens
    total_comp += stats.compressed_tokens
    print(
        f"{name:<26} {stats.original_tokens:>8} {'->':>2} "
        f"{stats.compressed_tokens:>10} {stats.savings_pct:>8.1f}% {stats.time_ms:>6.2f}ms"
    )

print("-" * len(header))
saved = total_orig - total_comp
pct = saved / total_orig * 100 if total_orig else 0
print(f"{'TOTAL':<26} {total_orig:>8} {'->':>2} {total_comp:>10} {pct:>8.1f}%")
