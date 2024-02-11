import { Account } from '../models/account';
import { Tag } from '../models/tag';
import { JsonTransaction } from '../types/JsonTransaction';

export class Transaction {
    uid: number = 0;
    account: Account;
    destination?: Account;
    payee: string = '';
    amount: number = 0;
    occurred_on: Date = new Date();
    cleared_on?: Date;
    note?: string;
    tags: Tag[] = [];
    selected: boolean = false;
    receipt_name?: string;
    receipt?: File;

    constructor(account: Account) {
        this.account = account;
    }

    static clone(transaction: Transaction): Transaction {
        const t = new Transaction(transaction.account);
        t.uid = transaction.uid;
        t.destination = transaction.destination;
        t.payee = transaction.payee;
        t.amount = transaction.amount;
        t.occurred_on = transaction.occurred_on;
        t.cleared_on = transaction.cleared_on;
        t.note = transaction.note;
        t.tags = transaction.tags;
        return t;
    }

    static fromJson(json: JsonTransaction): Transaction {
        const account = Account.fromJson(json.account);
        const t = new Transaction(account);
        t.uid = json.uid;

        if (json.destination) {
            t.destination = Account.fromJson(json.destination);
        }

        t.payee = json.payee;

        t.amount = json.amount

        t.occurred_on = new Date(json.occurred_on);

        if (json.cleared_on) {
            t.cleared_on = new Date(json.cleared_on);
        }

        if (json.note) {
            t.note = json.note;
        }

        t.tags = json.tags.map((tag) => Tag.fromString(tag));

        if (json.receipt_name) {
            t.receipt_name = json.receipt_name;
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
            formData.append('tags', tag.name);
        }

        if (this.receipt) {
            formData.set('receipt', this.receipt);
        }

        return formData;

    }
}
