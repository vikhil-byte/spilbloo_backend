# Database Seeding Commands

You can use these commands to populate your database with initial data.

## All-in-One Command
Run everything at once:
```bash
python3 manage.py seed_all
```

## Individual Commands
If you need to seed specific modules:

| Command | Description | App |
|---------|-------------|-----|
| `python3 manage.py seed_users` | Seeds initial user accounts | `accounts` |
| `python3 manage.py seed_symptoms` | Seeds common medical symptoms | `core` |

## How to add new seeds
1. Create a new command file in the relevant app's `management/commands/` folder.
2. Add your command name to the `commands` list in `core/management/commands/seed_all.py`.
