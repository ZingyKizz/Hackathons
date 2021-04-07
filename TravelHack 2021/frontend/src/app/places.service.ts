import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Place } from './place';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PlacesService {
  Url = "http://127.0.0.1:5000";
  places: Place[] = [];
  ids: number[] = [];
  constructor(private http: HttpClient) { }
  getPlaces(): Observable<Place[]> {
    return this.http.post<Place[]>(this.Url + "/history", {"history": this.ids})
  }
  getPlace(id: any): Observable<Place[]> {
    return this.http.get<Place[]>(this.Url + "/place?id="+id)
  }
  clickPlace(id: number) {
    this.ids.push(id);
  }
}
