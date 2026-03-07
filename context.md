# Project Context - Backend

## User Roles (`role_id`)
Backend role constants are defined in `accounts/models.py`:

| role_id | Constant       | Label   |
|--------|----------------|---------|
| 0      | ROLE_ADMIN     | Admin   |
| 1      | ROLE_MANAGER   | Manager |
| 2      | ROLE_USER      | User    |
| 3      | ROLE_CLIENT    | Client  |
| 4      | ROLE_PATIENT   | Patient |
| 5      | ROLE_DOCTER    | Doctor  |

## Gender Mapping (`gender`)
Mapped from legacy PHP system:
- **0**: Other
- **1**: Male
- **2**: Female
- **3**: Transgender Male
- **4**: Transgender Female
- **5**: Gender Queer
- **6**: Non Binary

## State Mapping (`state_id`)
- **0**: Inactive
- **1**: Active
- **2**: Banned
- **3**: Deleted

## Key Modules
- **accounts**: User management, authentication, and profiles.
- **plans**: Subscription and billing logic.
- **availability**: Therapist scheduling and bookings.
