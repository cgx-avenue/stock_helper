from tortoise import fields,models


class stock_trading_record(models.Model):
    id = fields.IntField(pk=True)
    action = fields.TextField()
    timestamp=fields.TextField()
    price = fields.FloatField()
    quantity=fields.IntField()
    amount=fields.FloatField()
    fee=fields.FloatField()
    code=fields.TextField()
    stock_name=fields.TextField()