import { Account } from '../models/account';
import { TransactionPrimitive } from '../types/transactionPrimitive';

export class Transaction {
    uid: number;
    account?: Account
    destination?: Account
    payee: string;
    amount: number;
    occurred_on: Date;
    cleared_on?: Date;
    note?: string;
    tags: string[];
    selected: boolean;

    constructor(primitive: TransactionPrimitive) {
        this.uid = primitive.uid;

        if (primitive.account) {
            this.account = new Account(primitive.account);
        }

        if (primitive.destination) {
            this.destination = new Account(primitive.destination);
        }

        this.payee = primitive.payee;

        this.amount = primitive.amount

        this.occurred_on = new Date(primitive.occurred_on);

        if (primitive.cleared_on) {
            this.cleared_on = new Date(primitive.cleared_on);
        }

        if (primitive.note) {
            this.note = primitive.note;
        }

        this.tags = (primitive.tags || []).filter((tag) => tag);

        this.selected = false
    }

    get accountId(): number {
        return this.account?.uid || 0;
    }

    get destinationId(): number {
        return this.destination?.uid || 0;
    }

    get locked(): boolean {
        return !!this.cleared_on;
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
}
