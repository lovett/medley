import { Account } from '../models/account';
import { TransactionPrimitive } from '../types/transactionPrimitive';

export class Transaction {
    uid: number;
    account: Account
    payee: string;
    amount: number;
    occurred_on: Date;
    cleared_on?: Date;
    note?: string;

    constructor(primitive: TransactionPrimitive) {
        this.uid = primitive.uid;
        this.account = new Account(primitive.account!);
        this.payee = primitive.payee;
        this.amount = primitive.amount;
        this.occurred_on = new Date(primitive.occurred_on);
        if (primitive.cleared_on) {
            this.cleared_on = new Date(primitive.cleared_on);
        }
        if (primitive.note) {
            this.note = primitive.note;
        }
    }

    toPrimitive(): TransactionPrimitive {
        return {
            uid: this.uid,
            account_id: this.account.uid,
            payee: this.payee,
            amount: this.amount,
            occurred_on: this.occurred_on.toISOString().split('T')[0],
            cleared_on: (this.cleared_on)? this.cleared_on.toISOString().split('T')[0] : undefined,
            note: this.note,
        };
    }
}
