import urllib
import urllib2
import cookielib
import sqlite3
import sys
from sgmllib import SGMLParser

DATABASE_FILE = 'cheltuilei'

class LCLDataFetcher:
	def __init__(self, agence, compte, code):
		self._agence = agence
		self._compte = compte
		self._code = code
		self._login_url = "https://particuliers.secure.lcl.fr/everest/UWBI/UWBIAccueil?DEST=IDENTIFICATION"
		self._data_url = ("https://particuliers.secure.lcl.fr/outil/UWLM/ListeMouvementsPar/accesListeMouvementsPar?agence=%s&compte=%sW&mode=06"
			%(agence, compte))
		self._cj = cookielib.LWPCookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self._cj))
		urllib2.install_opener(opener)

	def UpdateCookie(self):
		values = {'agenceId' : self._agence, 'serviceId' : 'CLI', 'compteId': self._compte, 'CodeId':self._code }
		data = urllib.urlencode(values)
		req = urllib2.Request(self._login_url, data)
		urllib2.urlopen(req)
		# Now the cookie has been populated automatically in the Cookie Jar.

	def GetAccountData(self):
		req = urllib2.Request(self._data_url)
		response = urllib2.urlopen(req)
		return response.read()
		

class ExpenseLister(SGMLParser):
	def reset(self):                              
		SGMLParser.reset(self)
		self.entries = []
		self._process_data = False
		self._item = 0
		self._in_td = False
		self._td_count = 0
		self._expenses = []

	def start_tr(self, attrs):
		class_attr = [v for k, v in attrs if k=='class']
		if class_attr and (class_attr[0] == 'tbl1' or class_attr[0] == 'tbl2'):
			self._process_data = True
			self._td_count = 0
	def end_tr(self):                     
		if self._process_data:
			self._process_data = False

	def start_td(self, attrs):
		self._td_count = self._td_count + 1
		if not self._process_data:
			return
		self._in_td = True
	def end_td(self):
		if not self._process_data:
			return
		self._in_td = False
	def handle_data(self, text):
		if self._in_td:
			if text.strip():
				txt = text.strip()
				if self._td_count == 3:
					txt = "-" + txt
				self.entries.append(txt)
	def get_expenses(self):
		def ParseValue(value):
			return float(value.replace(',', '.').replace("\xc2\xa0", ''))
		if not self._expenses:
			for i in range(0, len(self.entries), 3):
				expense = [self.entries[i], self.entries[i + 1], ParseValue(self.entries[i + 2])]
				self._expenses.append(expense)
		return self._expenses
			

class SQLWriter:
	def __init__(self, filename):
		self._connection = sqlite3.connect(filename)
		cursor = self._connection.cursor()
		try:
			cursor.execute("select * from cheltuieli")
		except sqlite3.OperationalError:
			#create database
			cursor.execute('create table cheltuieli(date date, name text, category text, sum real)')
		self._connection.commit()
		cursor.close()
	def addItem(self, item):
		cursor = self._connection.cursor()
		cursor.execute('select * from cheltuieli where date=? and name=? and category=? and sum=?', item)
		if cursor.fetchone():
			return False
		cursor.execute('insert into cheltuieli values (?,?,?,?)', item)
		self._connection.commit()
		cursor.close()
		return True
			
def OneOfInName(item_list, name):
	for item in item_list:
		if item in name:
			return True
		return False
def ParseExpense(expense):
	restaurante = ['PIZZA', 'KFC', 'ALLORESTO']
	facturi = ["PRLV GROUPAMA", "PRLV EDF", "PRLV Free", "PRLV VIRGIN"]
	category = "no_category"
	name = expense[1]
	if "FRANPRIX" in name or "MONOPRIX" in name:
		category = "EPICERIE"
        elif "TRUFFAUT" in name:
                category = "FLEURS"
	elif "RETRAIT" in name:
		category = "CASH"
	elif "VIREMENT AMARAND" in name:
		category = "ECONOMIE"
	elif "ASSURANCE CAPITAL MULTICOMPTES" in name or "LCL A LA CARTE" in name:
		category = "LCL"
	elif OneOfInName(facturi, name):
		category = "FACTURI"
	elif "AMAZON" in name:
		category = "BOOKS & STUFF"
	elif "AIR FRANCE" in name:
		category = "VOYAGE"
	elif "CMP IMMOBILIER" in name:
		category = "CHIRIE"
	elif "VIR" in name:
		category = "DATORII"
	elif OneOfInName(restaurante, name):
		category = 'RESTAURANT'
	return [name, expense[1], category, expense[2]]

def main():
	if len(sys.argv) < 4:
		sys.stderr.write('Usage: %s agence compte code [database_file]\n'%sys.argv[0])
		sys.exit(1)
	fetcher = LCLDataFetcher(sys.argv[1], sys.argv[2], sys.argv[3])
	fetcher.UpdateCookie()
	page = fetcher.GetAccountData()
	#print page
	parser = ExpenseLister()
	parser.feed(page)
	expenses = parser.get_expenses()
	database_file = DATABASE_FILE
	if len(sys.argv) == 5:
		database_file = sys.argv[4]
	sql_writer = SQLWriter(database_file)
	new_expenses = []
	processed_expenses = []
	for expense in expenses:
		if expense in processed_expenses:
			continue
		processed_expenses.append(expense)
		# some expenses, like air france tickets appear in double
		# only register one expense in this case
		expense_count = expenses.count(expense)
		for i in range(0, expense_count - 1):
			expenses.remove(expense)
		expense[-1] = expense[-1] * expense_count
		parsed_expense = ParseExpense(expense)
		if sql_writer.addItem(parsed_expense):
			new_expenses.append(parsed_expense)
	if new_expenses:
		print '\n'.join(';'.join(str(entry).replace(".",",") for entry in tpl) for tpl in new_expenses)
	
	
if __name__ == '__main__':
	main()