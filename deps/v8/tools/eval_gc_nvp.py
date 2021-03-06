#!/usr/bin/env python
#
# Copyright 2015 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is used to analyze GCTracer's NVP output."""


from argparse import ArgumentParser
from copy import deepcopy
from gc_nvp_common import split_nvp
from math import log
from sys import stdin


class LinearBucket:
  def __init__(self, granularity):
    self.granularity = granularity

  def value_to_bucket(self, value):
    return int(value / self.granularity)

  def bucket_to_range(self, bucket):
    return (bucket * self.granularity, (bucket + 1) * self.granularity)


class Log2Bucket:
  def __init__(self, start):
    self.start = int(log(start, 2)) - 1

  def value_to_bucket(self, value):
    index = int(log(value, 2))
    index -= self.start
    if index < 0:
      index = 0
    return index

  def bucket_to_range(self, bucket):
    if bucket == 0:
      return (0, 2 ** (self.start + 1))
    bucket += self.start
    return (2 ** bucket, 2 ** (bucket + 1))


class Histogram:
  def __init__(self, bucket_trait, fill_empty):
    self.histogram = {}
    self.fill_empty = fill_empty
    self.bucket_trait = bucket_trait

  def add(self, key):
    index = self.bucket_trait.value_to_bucket(key)
    if index not in self.histogram:
      self.histogram[index] = 0
    self.histogram[index] += 1

  def __str__(self):
    ret = []
    keys = self.histogram.keys()
    keys.sort()
    last = keys[len(keys) - 1]
    for i in range(0, last + 1):
      (min_value, max_value) = self.bucket_trait.bucket_to_range(i)
      if i == keys[0]:
        keys.pop(0)
        ret.append("  [{0},{1}[: {2}".format(
          str(min_value), str(max_value), self.histogram[i]))
      else:
        if self.fill_empty:
          ret.append("  [{0},{1}[: {2}".format(
            str(min_value), str(max_value), 0))
    return "\n".join(ret)


class Category:
  def __init__(self, key, histogram):
    self.key = key
    self.values = []
    self.histogram = histogram

  def process_entry(self, entry):
    if self.key in entry:
      self.values.append(float(entry[self.key]))
      if self.histogram:
        self.histogram.add(float(entry[self.key]))

  def __str__(self):
    ret = [self.key]
    ret.append("  len: {0}".format(len(self.values)))
    if len(self.values) > 0:
      ret.append("  min: {0}".format(min(self.values)))
      ret.append("  max: {0}".format(max(self.values)))
      ret.append("  avg: {0}".format(sum(self.values) / len(self.values)))
      if self.histogram:
        ret.append(str(self.histogram))
    return "\n".join(ret)


def main():
  parser = ArgumentParser(description="Process GCTracer's NVP output")
  parser.add_argument('keys', metavar='KEY', type=str, nargs='+',
                      help='the keys of NVPs to process')
  parser.add_argument('--histogram-type', metavar='<linear|log2>',
                      type=str, nargs='?', default="linear",
                      help='histogram type to use (default: linear)')
  linear_group = parser.add_argument_group('linear histogram specific')
  linear_group.add_argument('--linear-histogram-granularity',
                            metavar='GRANULARITY', type=int, nargs='?',
                            default=5,
                            help='histogram granularity (default: 5)')
  log2_group = parser.add_argument_group('log2 histogram specific')
  log2_group.add_argument('--log2-histogram-init-bucket', metavar='START',
                          type=int, nargs='?', default=64,
                          help='initial buck size (default: 64)')
  parser.add_argument('--histogram-omit-empty-buckets',
                      dest='histogram_omit_empty',
                      action='store_true',
                      help='omit empty histogram buckets')
  parser.add_argument('--no-histogram', dest='histogram',
                      action='store_false', help='do not print histogram')
  parser.set_defaults(histogram=True)
  parser.set_defaults(histogram_omit_empty=False)
  args = parser.parse_args()

  histogram = None
  if args.histogram:
    bucket_trait = None
    if args.histogram_type == "log2":
      bucket_trait = Log2Bucket(args.log2_histogram_init_bucket)
    else:
      bucket_trait = LinearBucket(args.linear_histogram_granularity)
    histogram = Histogram(bucket_trait, not args.histogram_omit_empty)

  categories = [ Category(key, deepcopy(histogram))
                 for key in args.keys ]

  while True:
    line = stdin.readline()
    if not line:
      break
    obj = split_nvp(line)
    for category in categories:
      category.process_entry(obj)

  for category in categories:
    print(category)


if __name__ == '__main__':
  main()
