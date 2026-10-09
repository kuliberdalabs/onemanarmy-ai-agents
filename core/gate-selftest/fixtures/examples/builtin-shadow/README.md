# builtin-shadow fixture

The `bin/` folder here is a fixture for the builtin-shadow demo. It holds an executable named `log` that shadows a command of the same name on purpose.

Never add `bin/` to your `PATH` outside this folder. The gate scripts here prepend it to `PATH` for their own run only.
