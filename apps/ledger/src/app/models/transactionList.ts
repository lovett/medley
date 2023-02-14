import { Transaction } from '../models/transaction';

export type TransactionList = {
    count: number,
    transactions: Transaction[]
}
