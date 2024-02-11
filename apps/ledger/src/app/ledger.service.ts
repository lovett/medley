import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { Account } from './models/account';
import { AccountList } from './types/AccountList';
import { Tag } from './models/tag';
import { JsonTag } from './types/JsonTag';
import { Transaction } from './models/transaction';
import { JsonTransaction }  from './types/JsonTransaction';
import { JsonAccount }  from './types/JsonAccount';
import { TransactionList } from './types/TransactionList';
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

    clearSelections() {
        this.selectedTransactions.forEach(t => t.selected = false);
        this.selectedTransactions = [];
        this.selectedSubject.next(Infinity);
    }

    transactionSelection(target: Transaction|null) {
        if (target == null) {
            this.clearSelections();
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
        return this.http.get<JsonTag[]>('/ledger/tags').pipe(
            map(jsonTags => jsonTags.map(jsonTag => Tag.fromJson(jsonTag)))
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
        return this.http.get<JsonAccount>(`/ledger/accounts/${uid}`).pipe(
            map((jsonAccount) => Account.fromJson(jsonAccount))
        );
    }

    getTransaction(uid: number): Observable<Transaction> {
        return this.http.get<JsonTransaction>(`/ledger/transactions/${uid}`).pipe(
            map((jsonTransaction) => Transaction.fromJson(jsonTransaction))
        );
    }

    saveAccount(account: Account): Observable<void> {
        const formData = account.asFormData();
        if (account.uid === 0) {
            return this.http.post<void>('/ledger/accounts', formData);
        }
        return this.http.put<void>(`/ledger/accounts/${account.uid}`, formData);
    }

    renameTag(oldTag: Tag, newTag: Tag): Observable<void> {
        const formData = newTag.asFormData();
        return this.http.put<void>(`/ledger/tags/${oldTag.name}`, formData);
    }

    saveTransaction(transaction: Transaction): Observable<void> {
        const formData = transaction.asFormData();
        if (transaction.uid === 0) {
            return this.http.post<void>('/ledger/transactions', formData);
        }

        return this.http.put<void>(`/ledger/transactions/${transaction.uid}`, formData);
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
}
