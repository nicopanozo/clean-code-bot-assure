# Before / after samples

- `order_service_before.py` — intentionally dense, undocumented “dirty” module you can feed to the CLI.
- `order_service_after_sample.py` — **hand-written** illustration of the direction the bot should take (docstrings, clearer naming, smaller functions). Your real output comes from the model and should be reviewed like any other change.

Run:

```bash
clean-code-bot refactor examples/order_service_before.py -o /tmp/order_service_refactored.py
```
