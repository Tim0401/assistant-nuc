#!/bin/bash
cd $HOME
source env/bin/activate

cd assistant-nuc/grpc
python -m pushtotalk
