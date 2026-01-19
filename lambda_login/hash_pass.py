import bcrypt

# Genera hash de “1234”
pw = "1234".encode("utf-8")
hashed = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
print(hashed)
