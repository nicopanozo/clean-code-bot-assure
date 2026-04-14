# checkout_svc.py — legacy path (Q4-22 hotfix). TODO: someone refactor this

class OSvc:
    def __init__(self, db, mail):
        self.db = db
        self.mail = mail

    def go(self, uid, items, pay):
        u = self.db.q("select * from users where id=?", uid)
        if not u:
            return {"e": "no user"}
        tot = 0
        for i in items:
            p = self.db.q("select price from products where id=?", i["pid"])
            if not p:
                return {"e": "bad product"}
            tot += p[0] * i["q"]
        if pay == "cc":
            ok = self.db.q("insert into charges (user,amt) values (?,?)", uid, tot)
            if not ok:
                return {"e": "charge fail"}
        elif pay == "po":
            if u[3] < tot:
                return {"e": "credit"}
        else:
            return {"e": "pay"}
        oid = self.db.q("insert into orders (user,total,pay) values (?,?,?)", uid, tot, pay)
        for i in items:
            self.db.q("insert into order_lines (order,pid,q) values (?,?,?)", oid, i["pid"], i["q"])
        self.mail.send(u[1], "order", str(oid))
        return {"ok": True, "id": oid, "t": tot}
