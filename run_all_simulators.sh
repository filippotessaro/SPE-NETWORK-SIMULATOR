#!/usr/bin/env bash

git checkout master;
echo aloha-normal;
# create dir to store the simulations files
mkdir aloha-normal;
# run the starting simulator NORMAL
for i in {0..30}; do python3 main.py -r $i; done;

# Pass to REALISTIC
echo aloha-realistic;
mkdir aloha-realistic;
git checkout aloha-realistic;
for i in {0..30}; do python3 main.py -r $i; done;

echo trivial-normal;
#echo trivial
git checkout trivial-normal;
# create dir to store the simulations files
mkdir trivial-normal;
# run the starting simulator
for i in {0..30}; do python3 main.py -r $i; done;

echo trivial-realistic;
git checkout trivial-realistic;
# create dir to store the simulations files
mkdir trivial-realistic;
# run the starting simulator
for i in {0..30}; do python3 main.py -r $i; done;

#-------------- R Script for Plotting ----------------
git checkout plot;
echo plotting-normal;
RScript plotting-normal.r ;

echo plotting-realistic;
RScript plotting-realistic.r ;

echo "Rscript-trivial carrier sensing normal";
RScript process.r ;
