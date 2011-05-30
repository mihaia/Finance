

clas TradeableItem:
	def __init__(self, name, isin, ticker):
		self._name = name
		self._isin = isin
		self._ticker = ticker
		self._values = {}
	def addValue(self, date, value):
		self._values[date] = value
	# it needs to be present, otherwise we have an exception
	def getValue(self, date):
		return self._values[date]
		
		
class Portfolio:
	def __init__(self, name):
		self._name = name
		self._items = []
	def addTradeableItem(self, item):
		self._items.append(item)
	def getValue(self, date):
		value = 0.0
		for item in self._items:
			value = value + item.getValue(date)
		return value
		
class ROIFitnessFunction:
	def __init__(self, start, end):
		self._start = start
		self._end = end
	def fitness(self, portfolio):
		initial_value = portfolio.getValue(self._start)
		final_value = portfolio.getValue(self._end)
		return (final_value - initial_value) / initial_value
	