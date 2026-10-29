state = "0"
a = "0"
while a != "9":
    b = "0"
    while b != "9":
        c = "0"
        while c != "9":
            d = "0"
            while d != "9":
                state = "1234567890"[int(state)]
                d = "1234567899"[int(d)]
            c = "1234567899"[int(c)]
        b = "1234567899"[int(b)]
    a = "1234567899"[int(a)]
print(state)
