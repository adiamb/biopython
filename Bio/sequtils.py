#!/usr/bin/env python
# Created: Sat Jul 21 08:01:13 2001
# Last changed: Time-stamp: <01/07/25 16:30:25 thomas>
# thomas@cbs.dtu.dk, Cecilia.Alsmark@ebc.uu.se
# Copyright 2001 by Thomas Sicheritz-Ponten and Cecilia Alsmark.
# All rights reserved.
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.
# File: sequtils.py

import os, sys, getopt, re, time
from Bio import Fasta
from Bio import Translate
from Bio.Seq import Seq
from Bio import Alphabet
from Bio.Alphabet import IUPAC
from Bio.Data import IUPACData, CodonTable
from PropertyManager import default_manager

"""

* sequtils is a temporary bucket for sequence utilities created by
  molecular biologs for molecular biologs.
  
* most functions can be used on multi FASTA files from the command line via the
  function multi_fasta_to.
   Usage: ./sequtils.py --apply_on_multi_fasta <name of function to call> <name of FASTA file>
   e.g.
      ./sequtils.py --apply_on_multi_fasta GC123 ../Scripts/xbbtools/test.fas

* to get a list of functions type: sequtils.py --describe

* for huge FASTA files (like complete genomes) use quick_FASTA_reader
  (on the command line --quick)
  
* functions starting with 'x' are graphical functions ... should definitely be
  moved elsewhere ...

* most functions should probably be moved into better locations
    ... someday ... someone ...

* functions to add:
   - primer calculation and selection
   - melting point
   - pattern matcher
   - sequence logos (thomas move pylogo)
   more suggestions ?

"""

# temporary hack for exception free translation of "dirty" DNA
# should be moved to ???

class ProteinX(Alphabet.ProteinAlphabet):
   letters = IUPACData.extended_protein_letters + "X"

proteinX = ProteinX()

class MissingTable:
  def __init__(self, table):
    self._table = table
  def get(self, codon, stop_symbol):
    try:
      return self._table.get(codon, stop_symbol)
    except CodonTable.TranslationError:
      return 'X'

def makeTableX(table):
  assert table.protein_alphabet == IUPAC.extended_protein
  return CodonTable.CodonTable(table.nucleotide_alphabet, proteinX,
                               MissingTable(table.forward_table),
                               table.back_table, table.start_codons,
                               table.stop_codons)



# end of hacks


def complement(seq):
   " returns the complementary sequence (NOT antiparallel) "
   return ''.join([IUPACData.ambiguous_dna_complement[x] for x in seq])

def reverse(seq):
   " reverse the sequence "
   r = map(None, seq)
   r.reverse()
   return ''.join(r)

def antiparallel(seq):
   " returns reversed complementary sequence ( = other strand ) "
   s = complement(seq)
   s = reverse(s)
   return s

def translate(seq, frame = 1, genetic_code = 1, translator = None):
   " translation of DNA in one of the six different reading frames "
   if frame not in [1,2,3,-1,-2,-3]:
      raise ValueError, 'invalid frame'

   if not translator:
      table = makeTableX(CodonTable.ambiguous_dna_by_id[genetic_code])
      translator = Translate.Translator(table)

   return translator.translate(Seq(seq[frame-1:], IUPAC.ambiguous_dna)).data

def GC_Frame(seq, genetic_code = 1):
   " just an alias for six_frame_translations "
   return six_frame_translations(seq, genetic_code)

def six_frame_translations(seq, genetic_code = 1):
   """
   nice looking 6 frame translation with GC content - code from xbbtools
   similar to DNA Striders six-frame translation
   """
   comp = complement(seq)
   anti = reverse(comp)
   length = len(seq)
   frames = {}
   for i in range(0,3):
      frames[i+1]  = translate(seq[i:], genetic_code)
      frames[-(i+1)] = reverse(translate(anti[i:], genetic_code))

   # create header
   if length > 20:
      short = '%s ... %s' % (seq[:10], seq[-10:])
   else:
      short = seq
   date = time.strftime('%y %b %d, %X', time.localtime(time.time()))
   header = 'GC_Frame: %s, ' % date
   for nt in ['a','t','g','c']:
      header += '%s:%d ' % (nt, seq.count(nt.upper()))
      
   header += '\nSequence: %s, %d nt, %0.2f %%GC\n\n\n' % (short.lower(),length, GC(seq))       
   res = header
   
   for i in range(0,length,60):
      subseq = seq[i:i+60]
      csubseq = comp[i:i+60]
      p = i/3
      res = res + '%d/%d\n' % (i+1, i/3+1)
      res = res + '  ' + '  '.join(map(None,frames[3][p:p+20])) + '\n'
      res = res + ' ' + '  '.join(map(None,frames[2][p:p+20])) + '\n'
      res = res + '  '.join(map(None,frames[1][p:p+20])) + '\n'
      # seq
      res = res + subseq.lower() + '%5d %%\n' % int(GC(subseq))
      res = res + csubseq.lower() + '\n'
      # - frames
      res = res + '  '.join(map(None,frames[-2][p:p+20]))  +' \n'
      res = res + ' ' + '  '.join(map(None,frames[-1][p:p+20])) + '\n'
      res = res + '  ' + '  '.join(map(None,frames[-3][p:p+20])) + '\n\n'
   return res
   
def GC(seq):
   " calculates G+C content "
   d = {}
   for nt in ['A','T','G','C']:
      d[nt] = seq.count(nt)
      gc = d.get('G',0) + d.get('C',0)

   if gc == 0: return 0
   return gc*100.0/(d['A'] +d['T'] + gc)
    
def GC123(seq):
   " calculates totla G+C content plus first, second and third position "
   l = len(seq)

   d= {}
   for nt in ['A','T','G','C']:
      d[nt] = [0,0,0]

   for i in range(0,l,3):
      codon = seq[i:i+3]
      if len(codon) <3: codon += '  '
      for pos in range(0,3):
         for nt in ['A','T','G','C']:
            if codon[pos] == nt: d[nt][pos] = d[nt][pos] +1


   gc = {}
   gcall = 0
   nall = 0
   for i in range(0,3):
      try:
         n = d['G'][i] + d['C'][i] +d['T'][i] + d['A'][i]
         gc[i] = (d['G'][i] + d['C'][i])*100.0/n
      except:
         gc[i] = 0

      gcall = gcall + d['G'][i] + d['C'][i]
      nall = nall + n

   gcall = 100.0*gcall/nall
   return gcall, gc[0], gc[1], gc[2]

def GC_skew(seq, window = 100):
   " calculates GC skew (G-C)/(G+C) "
   values = []
   for i in range(0, len(seq), window):
      s = seq[i: i + window]
      g = s.count('G')
      c = s.count('C')
      skew = (g-c)/float(g+c)
      values.append(skew)
   return values

def xGC_skew(seq, window = 1000, zoom = 100, 
                         r = 300, px = 100, py = 100):
   " calculates and plots normal and accumulated GC skew (GRAPHICS !!!) "
   
   from Tkinter import *
   from math import pi, sin, cos, log

   yscroll = Scrollbar(orient = VERTICAL)
   xscroll = Scrollbar(orient = HORIZONTAL)
   canvas = Canvas(yscrollcommand = yscroll.set,
                   xscrollcommand = xscroll.set, background = 'white')
   win = canvas.winfo_toplevel()
   win.geometry('700x700')
   
   yscroll.config(command = canvas.yview)
   xscroll.config(command = canvas.xview)
   yscroll.pack(side = RIGHT, fill = Y)
   xscroll.pack(side = BOTTOM, fill = X)        
   canvas.pack(fill=BOTH, side = LEFT, expand = 1)
   canvas.update()

   X0, Y0  = r + px, r + py
   x1, x2, y1, y2 = X0 - r, X0 + r, Y0 -r, Y0 + r
   
   ty = Y0
   canvas.create_text(X0, ty, text = '%s...%s (%d nt)' % (seq[:7], seq[-7:], len(seq)))
   ty +=20
   canvas.create_text(X0, ty, text = 'GC %3.2f%%' % (GC(seq)))
   ty +=20
   canvas.create_text(X0, ty, text = 'GC Skew', fill = 'blue')
   ty +=20
   canvas.create_text(X0, ty, text = 'Accumulated GC Skew', fill = 'magenta')
   ty +=20
   canvas.create_oval(x1,y1, x2, y2)

   acc = 0
   start = 0
   for gc in GC_skew(seq, window):
      r1 = r
      acc+=gc
      # GC skew
      alpha = pi - (2*pi*start)/len(seq)
      r2 = r1 - gc*zoom
      x1 = X0 + r1 * sin(alpha)
      y1 = Y0 + r1 * cos(alpha)
      x2 = X0 + r2 * sin(alpha)
      y2 = Y0 + r2 * cos(alpha)
      canvas.create_line(x1,y1,x2,y2, fill = 'blue')
      # accumulated GC skew
      r1 = r - 50
      r2 = r1 - acc
      x1 = X0 + r1 * sin(alpha)
      y1 = Y0 + r1 * cos(alpha)
      x2 = X0 + r2 * sin(alpha)
      y2 = Y0 + r2 * cos(alpha)
      canvas.create_line(x1,y1,x2,y2, fill = 'magenta')

      canvas.update()
      start = start + window
      

   canvas.configure(scrollregion = canvas.bbox(ALL))
   
def molecular_weight(seq):
   if type(seq) == type(''): seq = Seq(seq, IUPAC.unambiguous_dna)
   weight_table = IUPACData.unambiguous_dna_weights
   sum = 0
   for x in seq:
      sum += weight_table[x]
   return sum

def nt_search(seq, subseq):
   """ search for a DNA subseq in sequence
       use ambiguous values (like N = A or T or C or G, R = A or G etc.)
       searches only on forward strand
   """
   pattern = ''
   for nt in subseq:
      value = IUPACData.ambiguous_dna_values[nt]
      if len(value) == 1:
         pattern += value
      else:
         pattern += '[%s]' % value

   pos = -1
   result = [pattern]
   l = len(seq)
   while 1:
      pos+=1
      s = seq[pos:]
      m = re.search(pattern, s)
      if not m: break
      pos += int(m.start(0))
      result.append(pos)

   return result

   
def fasta_uniqids(file):
   " checks and changes the name/ID's to be unique identifiers by adding numbers "
   dict = {}
   txt = open(file).read()
   entries = []
   for entry in txt.split('>')[1:]:
      name, seq= entry.split('\n',1)
      name = name.split()[0].split(',')[0]
      
      if dict.has_key(name):
         n = 1
         while 1:
            n = n + 1
            _name = name + str(n)
            if not dict.has_key(_name):
               name = _name
               break
            
      dict[name] = seq

   for name, seq in dict.items():
      print '>%s\n%s' % (name, seq)

def quick_FASTA_reader(file):
   " simple and FASTA reader, preferable to be used on large files "
   txt = open(file).read()
   entries = []
   for entry in txt.split('>')[1:]:
      name,seq= entry.split('\n',1)
      seq = seq.replace('\n','').replace(' ','').upper()
      entries.append((name, seq))
      
   return entries
    
def apply_on_multi_fasta(file, function, *args):
   " apply function on each sequence in a multiple FASTA file "
   try:
      f = globals()[function]
   except:
      raise NotImplementedError, "%s not implemented" % function
   
   parser = Fasta.RecordParser()
   handle = open(file, 'r')
   iter = Fasta.Iterator(handle, parser)
   results = []
   while 1:
      record = iter.next()
      if not record: break
      arguments = [record.sequence]
      for arg in args: arguments.append(arg)
      result = apply(f, arguments)
      if result:
         results.append('>%s\n%s' % (record.title, result))
   return results
         
def quicker_apply_on_multi_fasta(file, function, *args):
   " apply function on each sequence in a multiple FASTA file "
   try:
      f = globals()[function]
   except:
      raise NotImplementedError, "%s not implemented" % function
   
   entries = quick_FASTA_reader(file)
   results = []
   for name, seq in entries:
      arguments = [seq]
      for arg in args: arguments.append(arg)
      result = apply(f, arguments)
      if result:
         results.append('>%s\n%s' % (record.title, result))
   return results
    
if __name__ == '__main__':
   # crude command line options to use most functions directly on a FASTA file
   options = {'apply_on_multi_fasta':0,
              'quick':0,
              'uniq_ids':0,
              }

   optlist, args = getopt.getopt(sys.argv[1:], '', ['describe', 'apply_on_multi_fasta=',
                                                    'help', 'quick', 'uniq_ids', 'search='])
   for arg in optlist:
      if arg[0] in ['-h', '--help']:
         pass
      elif arg[0] in ['--describe']:
         # get all new functions from this file
         mol_funcs = [x[0] for x in locals().items() if type(x[1]) == type(GC)]
         mol_funcs.sort()
         print 'available functions:'
         for f in mol_funcs: print '\t--%s' % f
         print '\n\ne.g.\n./sequtils.py  --apply_on_multi_fasta GC test.fas'

         sys.exit(0)
      elif arg[0] in ['--apply_on_multi_fasta']:
         options['apply_on_multi_fasta'] = arg[1]
      elif arg[0] in ['--search']:
         options['search'] = arg[1]
      else:
         key = re.search('-*(.+)', arg[0]).group(1)
         options[key] = 1

         
   if options.get('apply_on_multi_fasta'):
      file = args[0]
      function = options['apply_on_multi_fasta']
      arguments = []
      if options.get('search'):
         arguments = options['search']
      if function == 'xGC_skew':
         arguments = 1000
      if options.get('quick'):
         results = quicker_apply_on_multi_fasta(file, function, arguments)
      else:
         results = apply_on_multi_fasta(file, function, arguments)
      for result in results: print result
      
   elif options.get('uniq_ids'):
      file = args[0]
      fasta_uniqids(file)

