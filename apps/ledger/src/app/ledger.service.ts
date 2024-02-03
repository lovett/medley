import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { Account } from './models/account';
import { AccountList } from './types/accountList';
import { Tag } from './models/tag';
import { TagPrimitive } from './types/tagPrimitive';
import { Transaction } from './models/transaction';
import { TransactionPrimitive }  from './types/transactionPrimitive';
import { AccountPrimitive }  from './types/accountPrimitive';
import { TransactionList } from './types/transactionList';
import { ReplaySubject } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class LedgerService {
    private selectedSubject = new ReplaySubject<number>();
    selection$ = this.selectedSubject.asObservable();
    selectedTransactions: Transaction[] = []

    constructor(
        private http: HttpClient
    ) {}

    transactionSelection(target: Transaction|null) {
        if (target == null) {
            this.selectedTransactions = [];
            this.selectedSubject.next(Infinity);
            return;
        }

        this.selectedTransactions = this.selectedTransactions.filter(
            t => t.uid !== target.uid
        );

        if (target.selected) {
            this.selectedTransactions.push(target);
            this.selectedSubject.next(target.amount);
            return;
        }

        this.selectedSubject.next(target.amount * -1);
    }

    getAccounts(): Observable<AccountList> {
        return this.http.get<AccountList>('/ledger/accounts');
    }

    getTags(): Observable<Tag[]> {
        return this.http.get<TagPrimitive[]>('/ledger/tags').pipe(
            map(primitives => primitives.map(primitive => new Tag(primitive)))
        );
    }

    getTransactions(query: string, limit: number, offset: number, account: number, tag: string): Observable<TransactionList> {
        let params = {};

        if (query) {
            params = {...params, 'q': query }
        }

        if (limit) {
            params = {...params, limit, }
        }

        if (offset) {
            params = {...params, offset, }
        }

        if (account) {
            params = {...params, account, }
        }

        if (tag) {
            params = {...params, tag, }
        }

        return this.http.get<TransactionList>('/ledger/transactions', {params,});
    }

    getAccount(uid: number): Observable<Account> {
        return this.http.get<AccountPrimitive>(`/ledger/accounts/${uid}`).pipe(
            map((primitive) => new Account(primitive))
        );
    }

    getTransaction(uid: number): Observable<Transaction> {
        return this.http.get<TransactionPrimitive>(`/ledger/transactions/${uid}`).pipe(
            map((primitive) => new Transaction(primitive))
        );
    }

    addAccount(primitive: AccountPrimitive): Observable<Account> {
        return this.http.post<Account>('/ledger/accounts', primitive)
    }

    addTransaction(primitive: TransactionPrimitive): Observable<Transaction> {
        return this.http.post<Transaction>('/ledger/transactions', primitive);
    }

    updateAccount(primitive: AccountPrimitive): Observable<void> {
        const url = `/ledger/accounts/${primitive.uid}`;
        return this.http.put<void>(url, primitive);
    }

    updateTransaction(primitive: TransactionPrimitive): Observable<void> {
        const formData = new FormData();
        formData.set('account_id', (primitive.account_id || '').toString());
        formData.set('destination_id', (primitive.destination_id || '').toString());
        formData.set('payee', primitive.payee);
        formData.set('amount', primitive.amount.toString());
        formData.set('occurred_on', primitive.occurred_on);

        formData.set('cleared_on', primitive.cleared_on || '');

        if (primitive.note) {
            formData.set('note', primitive.note);
        }

        for (const tag of primitive.tags) {
            formData.append('tags', tag);
        }

        if (primitive.receipt) {
            formData.set('receipt', primitive.receipt);
        }

        return this.http.put<void>(
            `/ledger/transactions/${primitive.uid}`,
            formData
        );
    }

    deleteAccount(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/accounts/${uid}`);
    }

    deleteTransaction(uid: number): Observable<void> {
        return this.http.delete<void>(`/ledger/transactions/${uid}`);
    }

    autocompletePayee(payee: string): Observable<TransactionList> {
        return this.http.get<TransactionList>(
            `/ledger/transactions?q=payee:${payee}&limit=1`
        );
    }

    renameTag(tag: Tag, name: string): Observable<void> {
        return this.http.patch<void>(`/ledger/tags/${tag.name}`, {name,});
    }
}
