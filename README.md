# auto-genote
Program to automatically check if a new grade has been published using genote, a website my school uses.

# Installation
Must create a `config.json` file based on `config.file.example` with your own login and password.

```bash
[GENERAL]
url = https://www.usherbrooke.ca/genote/application/etudiant/cours.php
form_id = authentification
save_file = save.file

[CREDENTIALS]
login = INSERT_LOGIN_HERE
password = INSERT_PASSWORD_HERE
```
