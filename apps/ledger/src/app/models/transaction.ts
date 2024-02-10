import { Account } from '../models/account';
import { TransactionPrimitive } from '../types/transactionPrimitive';

export class Transaction {
    uid: number = 0;
    account: Account | null = null;
    destination: Account | null = null;
    payee: string = '';
    amount: number = 0;
    occurred_on: Date = new Date();
    cleared_on?: Date;
    note?: string;
    tags: string[] = [];
    selected: boolean = false;
    receipt_name?: string;
    receipt?: File;

    constructor() {
    }

    static fromTransaction(transaction: Transaction): Transaction {
        const t = new Transaction();
        t.uid = transaction.uid;
        t.account = transaction.account;
        t.destination = transaction.destination;
        t.payee = transaction.payee;
        t.amount = transaction.amount;
        t.occurred_on = transaction.occurred_on;
        t.cleared_on = transaction.cleared_on;
        t.note = transaction.note;
        t.tags = transaction.tags;
        return t;
    }

    static fromPrimitive(primitive: TransactionPrimitive): Transaction {
        const t = new Transaction();
        t.uid = primitive.uid;

        if (primitive.account) {
            t.account = new Account(primitive.account);
        }

        if (primitive.destination) {
            t.destination = new Account(primitive.destination);
        }

        t.payee = primitive.payee;

        t.amount = primitive.amount

        t.occurred_on = new Date(primitive.occurred_on);

        if (primitive.cleared_on) {
            t.cleared_on = new Date(primitive.cleared_on);
        }

        if (primitive.note) {
            t.note = primitive.note;
        }

        t.tags = (primitive.tags || []).filter((tag) => tag);

        if (primitive.receipt_name) {
            t.receipt_name = primitive.receipt_name;
        }
        return t;
    }

    get accountId(): number {
        return this.account?.uid || 0;
    }

    get destinationId(): number {
        return this.destination?.uid || 0;
    }

    occurredOnYMD(): string {
        return this.dateValue(this.occurred_on);
    }

    clearedOnYMD(): string {
        return this.dateValue(this.cleared_on);
    }

    dateValue(d?: Date): string {
        if (!d) {
            return '';
        }

        return d.toISOString().split('T')[0];
    }

    toPrimitive(): TransactionPrimitive {
        return {
            uid: this.uid,
            account_id: this.accountId,
            destination_id: this.destinationId,
            payee: this.payee,
            amount: this.amount,
            occurred_on: this.occurred_on.toISOString().split('T')[0],
            cleared_on: (this.cleared_on)? this.cleared_on.toISOString().split('T')[0] : undefined,
            note: this.note,
            tags: this.tags,
        };
    }

    asFormData(): FormData {
        const formData = new FormData();
        if (this.account) {
            formData.set('account_id', this.account.uid.toString());
        }

        if (this.destination && this.destination.uid) {
            formData.set('destination_id', this.destination.uid.toString());
        }

        formData.set('payee', this.payee);
        formData.set('amount', this.amount.toString());
        formData.set('occurred_on', this.occurred_on.toString());

        if (this.cleared_on) {
            formData.set('cleared_on', this.cleared_on.toString());
        } else {
            formData.set('cleared_on', '');
        }

        if (this.note) {
            formData.set('note', this.note);
        }

        for (const tag of this.tags) {
            formData.append('tags', tag);
        }

        if (this.receipt) {
            formData.set('receipt', this.receipt);
        }

        return formData;

    }
}
