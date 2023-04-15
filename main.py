from argparse import ArgumentParser
from collections import namedtuple
import csv
import datetime as dt
from pprint import pprint


class Position(object):
    def __init__(self, open_time, qty, open_px, close_time, close_px, precision):
        self.open_time = open_time
        self.qty = qty # in ticks
        self.open_px = open_px
        self.close_time = close_time
        self.close_px = close_px
        self.precision = precision

    def __str__(self):
        return f'opened {self.open_time}: {to_units(self.qty, self.precision)} @ {self.open_px}; closed {self.close_time} for {self.close_px}'

    def __repr__(self):
        return f'Position({self.open_time},{to_units(self.qty, self.precision)},{self.open_px},{self.close_time},{self.close_px},{self.precision}'

    def to_row(self):
        return (self.open_time, self.close_time, to_units(self.qty, self.precision), self.open_px, self.close_px)


class Transaction(object):
    def __init__(self, time, qty, px, precision):
        self.time = time
        self.qty = qty # in ticks
        self.px = px
        self.precision = precision

    def __str__(self):
        return f'{self.time}: {to_units(self.qty, self.precision)} @ {self.px}'

    def __repr__(self):
        return f'Transaction({self.time},{to_units(self.qty, self.precision)},{self.px},{self.precision})'

    def to_row(self):
        return (self.time, to_units(self.qty, self.precision), self.px)


def excel_to_datetime(ordinal, epoch=dt.datetime(1900, 1, 1)):
    if ordinal > 59:
        ordinal -= 1 # Excel leap year bug, 1900 is NOT a leap year
    inDays = int(ordinal)
    frac = ordinal - inDays
    inSecs = int(round(frac * 86400.0))

    return epoch + dt.timedelta(days=inDays - 1, seconds=inSecs) # epoch is day 1


def to_ticks(value, precision):
    # converts value to an integer, rounded to nearest "tick".
    # One "tick" is 10**(-precision)
    return round(value*10**precision)

def to_units(ticks, precision):
    # inverse of to_ticks
    return ticks/10**precision

# LONG-only trading
def run(input_filename, output_filename, precision):
    with open(input_filename, newline='') as infile:
        reader = csv.reader(infile, quoting=csv.QUOTE_NONNUMERIC)
        rows = [r for r in reader]

    buys = [Transaction(r[0],to_ticks(r[1], precision),r[2]/r[1], precision) for r in rows if r[1] > 0]
    sells = [Transaction(r[0],to_ticks(-r[1], precision),-r[2]/r[1], precision) for r in rows if r[1] < 0]

    # sort buys and sells by time
    buys = sorted(buys, key = lambda t: t.time)
    sells = sorted(sells, key = lambda t: t.time)

    open_positions = [Position(b.time, b.qty, b.px, None, None, precision) for b in buys]
    closed_positions = []

    for s in sells:
        pprint(s)
        while s.qty > 0:
            p = open_positions.pop(0)
            pprint(p)
            if s.qty >= p.qty:
                s.qty -= p.qty
                cp = Position(p.open_time, p.qty, p.open_px, s.time, s.px, precision)
                closed_positions.append(cp)
            else:
                resid = Position(p.open_time, p.qty-s.qty, p.open_px, None, None, precision)
                open_positions.insert(0,resid)
                cp = Position(p.open_time, s.qty, p.open_px, s.time, s.px, precision)
                closed_positions.append(cp)
                s.qty=0

    with open(output_filename, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['OPEN_TIME','CLOSE_TIME','QTY','OPEN_PX','CLOSE_PX'])
        writer.writerows([c.to_row() for c in closed_positions])
        writer.writerows([o.to_row() for o in open_positions])

    #return open_positions, closed_positions


if __name__ == '__main__':
    parser = ArgumentParser(description='Read transaction record and output FIFO PnL')
    parser.add_argument(dest='input_filename', help='csv file with transactions; columns are DATE, QTY, DOLLAR_AMOUNT; QTY>0 is buy, QTY<0 is sell; DOLLAR_AMOUNT is always positive')
    parser.add_argument(dest='output_filename', help='output file with FIFO assigned PnL')
    parser.add_argument('-p', '--precision', type=int, default=8, help='max precision (defaults to 8)')

    args = parser.parse_args()

    run(args.input_filename, args.output_filename, args.precision)
