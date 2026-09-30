# donations/models.py
#
# There are no Django ORM models in this app any more — Product,
# Transaction and OrderItem now live in Firestore instead of a SQL
# database. See:
#
#   donations/firestore_client.py   — Firebase connection
#   donations/firestore_data.py     — all reads/writes (this is the
#                                      module views.py actually calls)
#
# This file is kept (empty of models) so `donations` remains an
# ordinary Django app — no migrations are generated or needed from it.
