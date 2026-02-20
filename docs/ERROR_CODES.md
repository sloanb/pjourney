# pjourney Error Codes

If something goes wrong, pjourney shows a notification in the bottom-right corner.
Note the reference code and include it in any support request.

| Code     | What it means                          | What to try                                      |
|----------|----------------------------------------|--------------------------------------------------|
| PJ-DB01  | Data could not be loaded               | Restart the app; contact support if it repeats   |
| PJ-DB02  | A change could not be saved            | Try again; check available disk space            |
| PJ-DB03  | An item could not be deleted           | Try again; contact support if it repeats         |
| PJ-DB04  | Database could not be opened           | Restart; ensure ~/.pjourney/ is writable         |
| PJ-DB05  | Database optimisation failed           | Try Vacuum again; your data is safe              |
| PJ-IO01  | Backup file could not be written       | Check available disk space                       |
| PJ-VAL01 | A number field has invalid text        | Correct the field and try saving again           |
| PJ-VAL02 | A date field has invalid text          | Enter the date as YYYY-MM-DD                     |
| PJ-APP01 | Unexpected internal error              | Restart the app; report the code to support      |
