import { Account } from '../models/account';

export type Transaction = {
    uid: number,
    account: Account,
    payee: string,
    amount: number,
    occurred_on: Date,
    cleared_on?: Date,
    note: string,
}
